import sqlite3


DATABASE = "wisata.db"

connection = sqlite3.connect(DATABASE)
cursor = connection.cursor()

cursor.executescript("""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS kriteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kode TEXT NOT NULL UNIQUE,
    nama TEXT NOT NULL,
    atribut TEXT NOT NULL CHECK (
        atribut IN ('benefit', 'cost')
    ),
    satuan TEXT
);

CREATE TABLE IF NOT EXISTS wisata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    alamat TEXT,
    deskripsi TEXT
);

CREATE TABLE IF NOT EXISTS penilaian (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wisata_id INTEGER NOT NULL,
    kriteria_id INTEGER NOT NULL,
    nilai REAL NOT NULL CHECK (nilai >= 0),

    FOREIGN KEY (wisata_id)
        REFERENCES wisata(id)
        ON DELETE CASCADE,

    FOREIGN KEY (kriteria_id)
        REFERENCES kriteria(id)
        ON DELETE CASCADE,

    UNIQUE (wisata_id, kriteria_id)
);
""")

data_kriteria = [
    ("C1", "Harga Tiket", "cost", "Rupiah"),
    ("C2", "Jarak", "cost", "Kilometer"),
    ("C3", "Fasilitas", "benefit", "Skala 1-5"),
    ("C4", "Rating", "benefit", "Skala 1-5"),
    ("C5", "Kebersihan", "benefit", "Skala 1-5"),
]

cursor.executemany("""
    INSERT OR IGNORE INTO kriteria (
        kode,
        nama,
        atribut,
        satuan
    )
    VALUES (?, ?, ?, ?)
""", data_kriteria)

data_wisata = [
    (
        "Wisata Curug Bayan",
        "Kabupaten Banyumas",
        "Tempat wisata alam untuk keluarga.",
        (25000, 17, 4, 4.5, 4),
    ),
    (
        "Wisata Baturaden Adventure Forest",
        "Kabupaten Banyumas",
        "Tempat wisata edukasi dan rekreasi.",
        (15000, 18, 3, 4.2, 4),
    ),
    (
        "Wisata Hutan Pinus Limpakuwus",
        "Kabupaten Banyumas",
        "Tempat wisata dengan pemandangan alam.",
        (10000, 22, 3, 4.0, 3),
    ),
    (
        "Wisata Lokawisata Baturaden",
        "Kabupaten Banyumas",
        "Tempat wisata keluarga dengan fasilitas lengkap.",
        (30000, 16, 5, 4.7, 5),
    ),
    (
        "Wisata Telaga Sunyi",
        "Kabupaten Banyumas",
        "Tempat wisata yang tenang dan nyaman.",
        (20000, 18, 4, 4.3, 4),
    ),
    (
        "Curug Jenggala",
        "Desa Ketenger, Kecamatan Baturraden",
        "Air terjun di kawasan Baturraden dengan suasana alam yang asri.",
        (15000, 19, 3, 4.4, 4),
    ),
    (
        "Curug Cipendok",
        "Desa Karangtengah, Kecamatan Cilongok",
        "Air terjun alami di kawasan lereng Gunung Slamet.",
        (15000, 27, 3, 4.5, 4),
    ),
    (
        "Small World Purwokerto",
        "Kawasan Baturraden, Kabupaten Banyumas",
        "Taman rekreasi dengan miniatur landmark dari berbagai negara.",
        (25000, 15, 5, 4.4, 4),
    ),
    (
        "Taman Andhang Pangrenan",
        "Purwokerto Selatan, Kabupaten Banyumas",
        "Ruang terbuka dan taman rekreasi di pusat Purwokerto.",
        (5000, 4, 4, 4.2, 4),
    ),
    (
        "Bukit Tranggulasih",
        "Desa Windujaya, Kecamatan Kedungbanteng",
        "Tempat menikmati pemandangan perbukitan di Banyumas.",
        (10000, 15, 2, 4.3, 3),
    ),
]

# Jarak merupakan estimasi rute jalan dari sekitar Pasar Wage, Purwokerto Timur.
# Nilai kriteria selain jarak tetap berupa data contoh simulasi.
kriteria_ids = {
    row[0]: row[1]
    for row in cursor.execute("SELECT kode, id FROM kriteria")
}
jarak_kriteria_id = kriteria_ids["C2"]

for nama, alamat, deskripsi, nilai_kriteria in data_wisata:
    wisata_row = cursor.execute(
        "SELECT id FROM wisata WHERE nama = ?",
        (nama,),
    ).fetchone()

    if wisata_row is None:
        cursor.execute(
            """
            INSERT INTO wisata (nama, alamat, deskripsi)
            VALUES (?, ?, ?)
            """,
            (nama, alamat, deskripsi),
        )
        wisata_id = cursor.lastrowid
    else:
        wisata_id = wisata_row[0]

    data_penilaian = [
        (wisata_id, kriteria_ids[f"C{nomor}"], nilai)
        for nomor, nilai in enumerate(nilai_kriteria, start=1)
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO penilaian (
            wisata_id,
            kriteria_id,
            nilai
        )
        VALUES (?, ?, ?)
    """, data_penilaian)

    cursor.execute(
        """
        UPDATE penilaian
        SET nilai = ?
        WHERE wisata_id = ? AND kriteria_id = ?
        """,
        (nilai_kriteria[1], wisata_id, jarak_kriteria_id),
    )

connection.commit()
connection.close()

print("Database wisata.db berhasil dibuat.")