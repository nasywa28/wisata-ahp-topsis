from flask import Flask, flash, render_template, request

from database import close_db, get_db
from services.ahp import hitung_ahp
from services.topsis import hitung_topsis


app = Flask(__name__)
app.config["SECRET_KEY"] = "secret-key-aplikasi-wisata"

# Menutup koneksi database setelah request selesai
app.teardown_appcontext(close_db)


@app.route("/")
def index():
    db = get_db()

    daftar_wisata = db.execute(
        """
        SELECT
            id,
            nama,
            alamat,
            deskripsi
        FROM wisata
        ORDER BY nama
        """
    ).fetchall()

    return render_template(
        "index.html",
        daftar_wisata=daftar_wisata,
    )


@app.route("/wisata")
def wisata():
    db = get_db()

    daftar_wisata = db.execute(
        """
        SELECT
            w.id,
            w.nama,
            w.alamat,
            w.deskripsi,

            MAX(
                CASE
                    WHEN k.kode = 'C1'
                    THEN p.nilai
                END
            ) AS harga,

            MAX(
                CASE
                    WHEN k.kode = 'C2'
                    THEN p.nilai
                END
            ) AS jarak,

            MAX(
                CASE
                    WHEN k.kode = 'C3'
                    THEN p.nilai
                END
            ) AS fasilitas,

            MAX(
                CASE
                    WHEN k.kode = 'C4'
                    THEN p.nilai
                END
            ) AS rating,

            MAX(
                CASE
                    WHEN k.kode = 'C5'
                    THEN p.nilai
                END
            ) AS kebersihan

        FROM wisata AS w

        LEFT JOIN penilaian AS p
            ON p.wisata_id = w.id

        LEFT JOIN kriteria AS k
            ON k.id = p.kriteria_id

        GROUP BY
            w.id,
            w.nama,
            w.alamat,
            w.deskripsi

        ORDER BY w.nama
        """
    ).fetchall()

    return render_template(
        "wisata.html",
        daftar_wisata=daftar_wisata,
    )


@app.route("/preferensi", methods=["GET", "POST"])
def preferensi():
    db = get_db()

    daftar_kriteria = db.execute(
        """
        SELECT
            id,
            kode,
            nama,
            atribut,
            satuan
        FROM kriteria
        ORDER BY id
        """
    ).fetchall()

    # Ketika halaman pertama kali dibuka
    if request.method == "GET":
        return render_template(
            "preferensi.html",
            daftar_kriteria=daftar_kriteria,
            nilai_terpilih={},
        )

    # Ketika tombol Hitung Rekomendasi ditekan
    print("=== POST DITERIMA ===")
    print("Data form:", request.form)

    try:
        jumlah_kriteria = len(daftar_kriteria)

        if jumlah_kriteria == 0:
            raise ValueError("Data kriteria belum tersedia.")

        # Membuat matriks awal dengan diagonal bernilai 1
        matriks_ahp = [
            [1.0 for _ in range(jumlah_kriteria)]
            for _ in range(jumlah_kriteria)
        ]

        # Membaca nilai perbandingan dari formulir
        for i in range(jumlah_kriteria):
            for j in range(i + 1, jumlah_kriteria):
                nama_input = f"perbandingan_{i}_{j}"
                nilai_form = request.form.get(nama_input)

                if nilai_form is None or nilai_form.strip() == "":
                    raise ValueError(
                        f"Perbandingan antara "
                        f"{daftar_kriteria[i]['nama']} dan "
                        f"{daftar_kriteria[j]['nama']} belum diisi."
                    )

                nilai = float(nilai_form)

                if nilai <= 0:
                    raise ValueError(
                        "Nilai perbandingan harus lebih dari nol."
                    )

                matriks_ahp[i][j] = nilai
                matriks_ahp[j][i] = 1.0 / nilai

        # Menghitung AHP
        hasil_ahp = hitung_ahp(matriks_ahp)

        print("Bobot AHP:", hasil_ahp["bobot"])
        print("Nilai CR:", hasil_ahp["cr"])

        # Mengambil daftar alternatif wisata
        daftar_wisata = db.execute(
            """
            SELECT
                id,
                nama,
                alamat,
                deskripsi
            FROM wisata
            ORDER BY id
            """
        ).fetchall()

        if len(daftar_wisata) == 0:
            raise ValueError("Data tempat wisata belum tersedia.")

        # Membentuk matriks keputusan TOPSIS
        matriks_keputusan = []

        for item_wisata in daftar_wisata:
            nilai_kriteria = db.execute(
                """
                SELECT
                    p.nilai
                FROM penilaian AS p

                INNER JOIN kriteria AS k
                    ON k.id = p.kriteria_id

                WHERE p.wisata_id = ?

                ORDER BY k.id
                """,
                (item_wisata["id"],),
            ).fetchall()

            if len(nilai_kriteria) != jumlah_kriteria:
                raise ValueError(
                    f"Data penilaian untuk "
                    f"{item_wisata['nama']} belum lengkap."
                )

            baris_matriks = [
                float(item["nilai"])
                for item in nilai_kriteria
            ]

            matriks_keputusan.append(baris_matriks)

        # Mengambil jenis atribut benefit atau cost
        atribut = [
            item["atribut"]
            for item in daftar_kriteria
        ]

        # Menghitung TOPSIS
        hasil_topsis = hitung_topsis(
            matriks_keputusan,
            hasil_ahp["bobot"],
            atribut,
        )

        # Menyusun hasil ranking
        hasil_ranking = []

        for indeks_numpy in hasil_topsis["ranking"]:
            indeks = int(indeks_numpy)

            hasil_ranking.append(
                {
                    "nama": daftar_wisata[indeks]["nama"],
                    "alamat": daftar_wisata[indeks]["alamat"],
                    "nilai": float(
                        hasil_topsis["nilai_preferensi"][indeks]
                    ),
                }
            )

        print("Hasil ranking:", hasil_ranking)
        print("=== MEMBUKA HASIL.HTML ===")

        return render_template(
            "hasil.html",
            daftar_kriteria=daftar_kriteria,
            daftar_wisata=daftar_wisata,
            matriks_keputusan=matriks_keputusan,
            hasil_ahp=hasil_ahp,
            hasil_topsis=hasil_topsis,
            hasil_ranking=hasil_ranking,
        )

    except (
        KeyError,
        ValueError,
        TypeError,
        ZeroDivisionError,
    ) as error:
        print("PERHITUNGAN GAGAL:", repr(error))

        flash(
            f"Perhitungan gagal: {error}",
            "danger",
        )

        return render_template(
            "preferensi.html",
            daftar_kriteria=daftar_kriteria,
            nilai_terpilih=request.form,
        )

    except Exception as error:
        print("KESALAHAN TIDAK TERDUGA:", repr(error))

        flash(
            f"Terjadi kesalahan pada sistem: {error}",
            "danger",
        )

        return render_template(
            "preferensi.html",
            daftar_kriteria=daftar_kriteria,
            nilai_terpilih=request.form,
        )


if __name__ == "__main__":
    app.run(debug=True)