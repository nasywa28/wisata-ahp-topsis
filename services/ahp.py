import numpy as np


RI_VALUES = {
    1: 0.00,
    2: 0.00,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}



def validasi_matriks(matriks):
    matriks = np.array(matriks, dtype=float)

    if matriks.ndim != 2:
        raise ValueError(
            "Matriks AHP harus memiliki dua dimensi."
        )

    if matriks.shape[0] != matriks.shape[1]:
        raise ValueError(
            "Mrus berbentuk persegi."
        )

    if np.any(matriks <= 0):
        raise ValueError(
            "Semua nilai matriks AHP harus lebih dari nol."
        )

    return matriks


def hitung_ahp(matriks):
    matriks = validasi_matriks(matriks)

    jumlah_kriteria = matriks.shape[0]

    rata_geometrik = np.exp(np.log(matriks).mean(axis=1))
    bobot = rata_geometrik / rata_geometrik.sum()
    matriks_normalisasi = matriks / matriks.sum(axis=0)

    nilai_eigen = np.linalg.eigvals(matriks)
    lambda_max = float(np.max(nilai_eigen.real))

    if jumlah_kriteria <= 2:
        consistency_index = 0.0
        consistency_ratio = 0.0
    else:
        consistency_index = max(
            0.0,
            (lambda_max - jumlah_kriteria) / (jumlah_kriteria - 1),
        )

        random_index = RI_VALUES.get(jumlah_kriteria)

        if random_index is None:
            raise ValueError(
                "Nilai Random Index belum tersedia."
            )

        consistency_ratio = (
            consistency_index / random_index
            if random_index != 0
            else 0.0
        )

    return {
        "matriks": matriks,
        "normalisasi": matriks_normalisasi,
        "bobot": bobot,
        "lambda_max": lambda_max,
        "ci": consistency_index,
        "cr": consistency_ratio,
        "konsisten": consistency_ratio <= 0.10,
    }