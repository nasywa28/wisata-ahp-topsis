import math

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from database import close_db, get_db
from services.ahp import hitung_ahp
from services.topsis import hitung_topsis


SKALA_PERBANDINGAN = (
    9,
    7,
    5,
    3,
    1,
    1 / 3,
    1 / 5,
    1 / 7,
    1 / 9,
)


app = Flask(__name__)
app.config["SECRET_KEY"] = "secret-key-aplikasi-wisata"

# Menutup koneksi database setelah request selesai
app.teardown_appcontext(close_db)


def validasi_form_wisata(form, daftar_kriteria):
    nama = form.get("nama", "").strip()
    alamat = form.get("alamat", "").strip()
    deskripsi = form.get("deskripsi", "").strip()
    nilai_kriteria = []
    kesalahan = []

    if not nama:
        kesalahan.append("Nama tempat wisata wajib diisi.")

    if not daftar_kriteria:
        kesalahan.append("Data kriteria belum tersedia.")

    for kriteria in daftar_kriteria:
        nilai_form = form.get(f"nilai_{kriteria['id']}", "").strip()

        if not nilai_form:
            kesalahan.append(
                f"Nilai untuk kriteria {kriteria['nama']} wajib diisi."
            )
            continue

        try:
            nilai = float(nilai_form)
        except ValueError:
            kesalahan.append(
                f"Nilai untuk kriteria {kriteria['nama']} harus berupa angka."
            )
            continue

        if not math.isfinite(nilai) or nilai < 0:
            kesalahan.append(
                f"Nilai untuk kriteria {kriteria['nama']} harus berupa "
                "angka nol atau lebih."
            )
            continue

        if kriteria["satuan"] == "Skala 1-5" and not 1 <= nilai <= 5:
            kesalahan.append(
                f"Nilai untuk kriteria {kriteria['nama']} harus berada "
                "pada skala 1 sampai 5."
            )
            continue

        nilai_kriteria.append((kriteria["id"], nilai))

    return (
        nama,
        alamat,
        deskripsi,
        nilai_kriteria,
        kesalahan,
    )


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


@app.route("/wisata", methods=["GET", "POST"])
def wisata():
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

    if request.method == "POST":
        (
            nama,
            alamat,
            deskripsi,
            nilai_kriteria,
            kesalahan,
        ) = validasi_form_wisata(request.form, daftar_kriteria)

        if kesalahan:
            for pesan in kesalahan:
                flash(pesan, "danger")
        else:
            with db:
                hasil_insert = db.execute(
                    """
                    INSERT INTO wisata (nama, alamat, deskripsi)
                    VALUES (?, ?, ?)
                    """,
                    (nama, alamat, deskripsi),
                )
                wisata_id = hasil_insert.lastrowid

                db.executemany(
                    """
                    INSERT INTO penilaian (wisata_id, kriteria_id, nilai)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (wisata_id, kriteria_id, nilai)
                        for kriteria_id, nilai in nilai_kriteria
                    ],
                )

            flash("Data tempat wisata berhasil ditambahkan.", "success")
            return redirect(url_for("wisata"))

    daftar_wisata = db.execute(
        """
        SELECT
            w.id,
            w.nama,
            w.alamat,
            w.deskripsi
        FROM wisata AS w
        ORDER BY w.nama
        """
    ).fetchall()

    nilai_per_wisata = db.execute(
        """
        SELECT
            p.wisata_id,
            p.kriteria_id,
            p.nilai
        FROM penilaian AS p
        INNER JOIN wisata AS w
            ON w.id = p.wisata_id
        ORDER BY w.nama, p.kriteria_id
        """
    ).fetchall()

    nilai_terkumpul = {}
    for item in nilai_per_wisata:
        nilai_terkumpul.setdefault(item["wisata_id"], {})[
            item["kriteria_id"]
        ] = item["nilai"]

    wisata_dengan_nilai = [
        {
            "id": item["id"],
            "nama": item["nama"],
            "alamat": item["alamat"],
            "deskripsi": item["deskripsi"],
            "nilai_kriteria": nilai_terkumpul.get(item["id"], {}),
        }
        for item in daftar_wisata
    ]

    return render_template(
        "wisata.html",
        daftar_wisata=wisata_dengan_nilai,
        daftar_kriteria=daftar_kriteria,
        nilai_terpilih=request.form if request.method == "POST" else {},
    )


@app.route("/wisata/<int:wisata_id>/edit", methods=["GET", "POST"])
def edit_wisata(wisata_id):
    db = get_db()
    item_wisata = db.execute(
        """
        SELECT id, nama, alamat, deskripsi
        FROM wisata
        WHERE id = ?
        """,
        (wisata_id,),
    ).fetchone()

    if item_wisata is None:
        abort(404)

    daftar_kriteria = db.execute(
        """
        SELECT id, kode, nama, atribut, satuan
        FROM kriteria
        ORDER BY id
        """
    ).fetchall()

    nilai_per_kriteria = {
        row["kriteria_id"]: row["nilai"]
        for row in db.execute(
            """
            SELECT kriteria_id, nilai
            FROM penilaian
            WHERE wisata_id = ?
            """,
            (wisata_id,),
        ).fetchall()
    }

    if request.method == "POST":
        (
            nama,
            alamat,
            deskripsi,
            nilai_kriteria,
            kesalahan,
        ) = validasi_form_wisata(request.form, daftar_kriteria)

        if kesalahan:
            for pesan in kesalahan:
                flash(pesan, "danger")
            nilai_terpilih = request.form
        else:
            with db:
                db.execute(
                    """
                    UPDATE wisata
                    SET nama = ?, alamat = ?, deskripsi = ?
                    WHERE id = ?
                    """,
                    (nama, alamat, deskripsi, wisata_id),
                )
                db.execute(
                    "DELETE FROM penilaian WHERE wisata_id = ?",
                    (wisata_id,),
                )
                db.executemany(
                    """
                    INSERT INTO penilaian (wisata_id, kriteria_id, nilai)
                    VALUES (?, ?, ?)
                    """,
                    [
                        (wisata_id, kriteria_id, nilai)
                        for kriteria_id, nilai in nilai_kriteria
                    ],
                )

            flash("Data tempat wisata berhasil diperbarui.", "success")
            return redirect(url_for("wisata"))
    else:
        nilai_terpilih = {
            "nama": item_wisata["nama"],
            "alamat": item_wisata["alamat"] or "",
            "deskripsi": item_wisata["deskripsi"] or "",
            **{
                f"nilai_{kriteria_id}": str(nilai)
                for kriteria_id, nilai in nilai_per_kriteria.items()
            },
        }

    return render_template(
        "edit_wisata.html",
        item_wisata=item_wisata,
        daftar_kriteria=daftar_kriteria,
        nilai_terpilih=nilai_terpilih,
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

    semua_wisata = db.execute(
        """
        SELECT id, nama, alamat, deskripsi
        FROM wisata
        ORDER BY nama
        """
    ).fetchall()
    indeks_kriteria = {
        item["id"]: indeks
        for indeks, item in enumerate(daftar_kriteria)
    }

    if request.method == "GET":
        return render_template(
            "preferensi.html",
            daftar_kriteria=daftar_kriteria,
            daftar_wisata=semua_wisata,
            kriteria_terpilih_ids={
                item["id"] for item in daftar_kriteria
            },
            wisata_terpilih_ids={
                item["id"] for item in semua_wisata
            },
            nilai_terpilih={},
        )

    print("=== POST DITERIMA ===")
    print("Data form:", request.form)

    kriteria_ids_tersedia = set(indeks_kriteria)
    wisata_ids_tersedia = {
        item["id"] for item in semua_wisata
    }
    kriteria_ids_diminta = set()
    wisata_ids_diminta = set()
    kesalahan_pilihan = []

    for raw_id in request.form.getlist("kriteria_terpilih"):
        try:
            kriteria_id = int(raw_id)
        except ValueError:
            kesalahan_pilihan.append("Pilihan kriteria tidak valid.")
            continue

        if kriteria_id not in kriteria_ids_tersedia:
            kesalahan_pilihan.append("Pilihan kriteria tidak ditemukan.")
        else:
            kriteria_ids_diminta.add(kriteria_id)

    for raw_id in request.form.getlist("wisata_terpilih"):
        try:
            wisata_id = int(raw_id)
        except ValueError:
            kesalahan_pilihan.append("Pilihan alternatif tidak valid.")
            continue

        if wisata_id not in wisata_ids_tersedia:
            kesalahan_pilihan.append("Pilihan alternatif tidak ditemukan.")
        else:
            wisata_ids_diminta.add(wisata_id)

    kriteria_terpilih = [
        item
        for item in daftar_kriteria
        if item["id"] in kriteria_ids_diminta
    ]
    wisata_terpilih = [
        item
        for item in semua_wisata
        if item["id"] in wisata_ids_diminta
    ]
    if not kriteria_terpilih:
        kesalahan_pilihan.append("Pilih minimal satu kriteria.")
    if not wisata_terpilih:
        kesalahan_pilihan.append("Pilih minimal satu alternatif wisata.")

    kriteria_indeks_terpilih = [
        indeks_kriteria[item["id"]]
        for item in kriteria_terpilih
    ]

    try:
        if kesalahan_pilihan:
            raise ValueError(" ".join(kesalahan_pilihan))

        jumlah_kriteria_terpilih = len(kriteria_terpilih)
        matriks_ahp = [
            [1.0 for _ in range(jumlah_kriteria_terpilih)]
            for _ in range(jumlah_kriteria_terpilih)
        ]

        for i in range(jumlah_kriteria_terpilih):
            for j in range(i + 1, jumlah_kriteria_terpilih):
                indeks_asli_i = kriteria_indeks_terpilih[i]
                indeks_asli_j = kriteria_indeks_terpilih[j]
                nama_input = f"perbandingan_{indeks_asli_i}_{indeks_asli_j}"
                posisi_form = request.form.get(f"{nama_input}_posisi")

                if posisi_form is not None:
                    try:
                        posisi = int(posisi_form)
                    except ValueError as error:
                        raise ValueError(
                            "Posisi perbandingan harus berupa bilangan bulat."
                        ) from error

                    if not 0 <= posisi < len(SKALA_PERBANDINGAN):
                        raise ValueError(
                            "Posisi perbandingan berada di luar skala."
                        )

                    nilai = SKALA_PERBANDINGAN[posisi]
                else:
                    nilai_form = request.form.get(nama_input)

                    if nilai_form is None or nilai_form.strip() == "":
                        raise ValueError(
                            f"Perbandingan antara "
                            f"{kriteria_terpilih[i]['nama']} dan "
                            f"{kriteria_terpilih[j]['nama']} belum diisi."
                        )

                    nilai = float(nilai_form)

                if nilai <= 0:
                    raise ValueError(
                        "Nilai perbandingan harus lebih dari nol."
                    )

                matriks_ahp[i][j] = nilai
                matriks_ahp[j][i] = 1.0 / nilai

        hasil_ahp = hitung_ahp(matriks_ahp)

        print("Bobot AHP:", hasil_ahp["bobot"])
        print("Nilai CR:", hasil_ahp["cr"])

        label_skala_ahp = (
            "9",
            "7",
            "5",
            "3",
            "1",
            "1/3",
            "1/5",
            "1/7",
            "1/9",
        )
        daftar_perbandingan = []
        for i in range(jumlah_kriteria_terpilih):
            for j in range(i + 1, jumlah_kriteria_terpilih):
                nilai_perbandingan = float(hasil_ahp["matriks"][i][j])
                posisi = min(
                    range(len(SKALA_PERBANDINGAN)),
                    key=lambda indeks: abs(
                        SKALA_PERBANDINGAN[indeks] - nilai_perbandingan
                    ),
                )
                cocok_dengan_skala = math.isclose(
                    SKALA_PERBANDINGAN[posisi],
                    nilai_perbandingan,
                    rel_tol=1e-7,
                )
                label_nilai = (
                    label_skala_ahp[posisi]
                    if cocok_dengan_skala
                    else f"{nilai_perbandingan:.4g}"
                )

                if math.isclose(nilai_perbandingan, 1.0):
                    keterangan = (
                        f"{kriteria_terpilih[i]['nama']} dan "
                        f"{kriteria_terpilih[j]['nama']} sama penting"
                    )
                elif nilai_perbandingan < 1:
                    keterangan = (
                        f"{kriteria_terpilih[j]['nama']} "
                        f"{1 / nilai_perbandingan:.4g}× lebih penting "
                        f"daripada {kriteria_terpilih[i]['nama']}"
                    )
                else:
                    keterangan = (
                        f"{kriteria_terpilih[i]['nama']} "
                        f"{label_nilai}× lebih penting daripada "
                        f"{kriteria_terpilih[j]['nama']}"
                    )

                daftar_perbandingan.append(
                    {
                        "kriteria_kiri": kriteria_terpilih[i],
                        "kriteria_kanan": kriteria_terpilih[j],
                        "nilai": nilai_perbandingan,
                        "label_nilai": label_nilai,
                        "posisi": posisi,
                        "keterangan": keterangan,
                    }
                )

        matriks_keputusan = []
        for item_wisata in wisata_terpilih:
            nilai_kriteria = {
                item["kriteria_id"]: float(item["nilai"])
                for item in db.execute(
                    """
                    SELECT
                        p.kriteria_id,
                        p.nilai
                    FROM penilaian AS p
                    WHERE p.wisata_id = ?
                    """,
                    (item_wisata["id"],),
                ).fetchall()
            }
            kriteria_tidak_dinilai = [
                item["nama"]
                for item in kriteria_terpilih
                if item["id"] not in nilai_kriteria
            ]
            if kriteria_tidak_dinilai:
                raise ValueError(
                    f"Data kriteria {', '.join(kriteria_tidak_dinilai)} "
                    f"untuk {item_wisata['nama']} belum lengkap."
                )

            baris_matriks = [
                nilai_kriteria[item["id"]]
                for item in kriteria_terpilih
            ]
            matriks_keputusan.append(baris_matriks)

        atribut = [
            item["atribut"]
            for item in kriteria_terpilih
        ]

        hasil_topsis = hitung_topsis(
            matriks_keputusan,
            hasil_ahp["bobot"],
            atribut,
        )

        hasil_ranking = []

        for indeks_numpy in hasil_topsis["ranking"]:
            indeks = int(indeks_numpy)

            hasil_ranking.append(
                {
                    "nama": wisata_terpilih[indeks]["nama"],
                    "alamat": wisata_terpilih[indeks]["alamat"],
                    "nilai": float(
                        hasil_topsis["nilai_preferensi"][indeks]
                    ),
                }
            )

        print("Hasil ranking:", hasil_ranking)
        print("=== MEMBUKA HASIL.HTML ===")

        return render_template(
            "hasil.html",
            daftar_kriteria=kriteria_terpilih,
            daftar_wisata=wisata_terpilih,
            daftar_perbandingan=daftar_perbandingan,
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
            daftar_wisata=semua_wisata,
            kriteria_terpilih_ids=kriteria_ids_diminta,
            wisata_terpilih_ids=wisata_ids_diminta,
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
            daftar_wisata=semua_wisata,
            kriteria_terpilih_ids=kriteria_ids_diminta,
            wisata_terpilih_ids=wisata_ids_diminta,
            nilai_terpilih=request.form,
        )


if __name__ == "__main__":
    app.run(debug=True)