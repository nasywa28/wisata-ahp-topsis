import numpy as np


def hitung_topsis(matriks, bobot, atribut):
    matriks = np.array(matriks, dtype=float)
    bobot = np.array(bobot, dtype=float)

    if matriks.ndim != 2:
        raise ValueError(
            "Matriks keputusan harus memiliki dua dimensi."
        )

    jumlah_alternatif, jumlah_kriteria = matriks.shape

    if jumlah_alternatif == 0:
        raise ValueError(
            "Data alternatif tidak tersedia."
        )

    if jumlah_kriteria != len(bobot):
        raise ValueError(
            "Jumlah bobot tidak sama dengan jumlah kriteria."
        )

    if jumlah_kriteria != len(atribut):
        raise ValueError(
            "Jumlah atribut tidak sama dengan jumlah kriteria."
        )

    if not np.isclose(bobot.sum(), 1.0):
        bobot = bobot / bobot.sum()

    pembagi = np.sqrt(
        np.sum(matriks ** 2, axis=0)
    )

    if np.any(pembagi == 0):
        raise ValueError(
            "Terdapat kriteria yang seluruh nilainya nol."
        )

    matriks_normalisasi = matriks / pembagi

    matriks_terbobot = matriks_normalisasi * bobot

    ideal_positif = np.zeros(jumlah_kriteria)
    ideal_negatif = np.zeros(jumlah_kriteria)

    for index, jenis in enumerate(atribut):
        kolom = matriks_terbobot[:, index]

        if jenis == "benefit":
            ideal_positif[index] = np.max(kolom)
            ideal_negatif[index] = np.min(kolom)

        elif jenis == "cost":
            ideal_positif[index] = np.min(kolom)
            ideal_negatif[index] = np.max(kolom)

        else:
            raise ValueError(
                "Atribut harus berupa benefit atau cost."
            )

    jarak_positif = np.sqrt(
        np.sum(
            (matriks_terbobot - ideal_positif) ** 2,
            axis=1
        )
    )

    jarak_negatif = np.sqrt(
        np.sum(
            (matriks_terbobot - ideal_negatif) ** 2,
            axis=1
        )
    )

    total_jarak = jarak_positif + jarak_negatif

    nilai_preferensi = np.divide(
        jarak_negatif,
        total_jarak,
        out=np.zeros_like(jarak_negatif),
        where=total_jarak != 0,
    )

    urutan_ranking = np.argsort(
        nilai_preferensi
    )[::-1]

    return {
        "normalisasi": matriks_normalisasi,
        "terbobot": matriks_terbobot,
        "ideal_positif": ideal_positif,
        "ideal_negatif": ideal_negatif,
        "jarak_positif": jarak_positif,
        "jarak_negatif": jarak_negatif,
        "nilai_preferensi": nilai_preferensi,
        "ranking": urutan_ranking,
    }