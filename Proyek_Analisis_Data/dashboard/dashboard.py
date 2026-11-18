from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

BASE_DIR = Path(__file__).parent

st.set_page_config(page_title="Analisis Penyewaan Sepeda 2011-2012", layout="wide")

# Warna dan gaya grafik
TEAL, AMBER, ABU, GELAP = "#0F766E", "#F59E0B", "#CBD5E1", "#1E293B"
sns.set_theme(
    style="whitegrid",
    rc={
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": ABU,
        "grid.color": "#E2E8F0",
        "axes.labelcolor": GELAP,
        "text.color": GELAP,
        "xtick.color": GELAP,
        "ytick.color": GELAP,
    },
)

NAMA_MUSIM = {1: "Spring", 2: "Summer", 3: "Fall", 4: "Winter"}
NAMA_CUACA = {1: "Cerah", 2: "Berkabut/Mendung", 3: "Hujan/Salju ringan"}
NAMA_HARI = {1: "Hari kerja", 0: "Akhir pekan/libur"}
WARNA_CUACA = {"Cerah": TEAL, "Berkabut/Mendung": "#7FB7B2", "Hujan/Salju ringan": AMBER}
WARNA_HARI = {"Hari kerja": TEAL, "Akhir pekan/libur": AMBER}
SEGMEN = ["Dini hari (00-05)", "Pagi (06-10)", "Siang (11-15)", "Sore (16-19)", "Malam (20-23)"]
KATEGORI = ["Sepi", "Normal", "Ramai"]


def legenda_bawah(ax, judul, kolom, jarak=-0.22):
    """Letakkan legenda di bawah grafik supaya tidak menutupi batang."""
    ax.legend(title=judul, frameon=False, loc="upper center", bbox_to_anchor=(0.5, jarak), ncol=kolom)


def angka(n):
    """Format angka dengan titik sebagai pemisah ribuan."""
    return f"{n:,.0f}".replace(",", ".")


@st.cache_data
def muat_data():
    day = pd.read_csv(BASE_DIR / "main_day.csv", parse_dates=["dteday"])
    hour = pd.read_csv(BASE_DIR / "main_hour.csv", parse_dates=["dteday"])

    for df in (day, hour):
        df["musim"] = pd.Categorical(
            df["season"].map(NAMA_MUSIM), categories=list(NAMA_MUSIM.values()), ordered=True
        )
        df["tipe_hari"] = df["workingday"].map(NAMA_HARI)

    day["cuaca"] = pd.Categorical(
        day["weathersit"].map(NAMA_CUACA), categories=list(NAMA_CUACA.values()), ordered=True
    )
    # Pengelompokan manual: jam menjadi segmen waktu, hari menjadi tingkat keramaian
    hour["segmen"] = pd.cut(hour["hr"], bins=[-1, 5, 10, 15, 19, 23], labels=SEGMEN)
    day["kategori"] = pd.cut(day["cnt"], bins=[0, 3000, 6000, float("inf")], labels=KATEGORI)
    return day, hour


day_all, hour_all = muat_data()
tgl_awal = day_all["dteday"].min().date()
tgl_akhir = day_all["dteday"].max().date()

# Sidebar: filter
with st.sidebar:
    st.title("Filter data")
    rentang = st.date_input(
        "Rentang tanggal",
        value=(tgl_awal, tgl_akhir),
        min_value=tgl_awal,
        max_value=tgl_akhir,
    )
    musim_dipilih = st.multiselect(
        "Musim", options=list(NAMA_MUSIM.values()), default=list(NAMA_MUSIM.values())
    )
    st.caption("Filter berlaku untuk semua tab.")

# date_input mengembalikan satu tanggal saja ketika rentang baru dipilih separuh
if len(rentang) != 2:
    st.info("Pilih tanggal awal dan tanggal akhir pada filter di samping.")
    st.stop()
if not musim_dipilih:
    st.warning("Pilih minimal satu musim.")
    st.stop()

mulai, selesai = pd.Timestamp(rentang[0]), pd.Timestamp(rentang[1])


def saring(df):
    return df[df["dteday"].between(mulai, selesai) & df["musim"].isin(musim_dipilih)]


day_f, hour_f = saring(day_all), saring(hour_all)
if day_f.empty:
    st.warning("Tidak ada data pada filter yang dipilih.")
    st.stop()

# Judul dan ringkasan angka
st.title("Penyewaan Sepeda 2011-2012")
st.caption("Pola penyewaan menurut cuaca, musim, dan jam, dari data harian dan data per jam.")

jam_rata = hour_f.groupby("hr")["cnt"].mean()
ringkasan = [
    ("Total penyewaan", angka(day_f["cnt"].sum())),
    ("Rata-rata per hari", angka(day_f["cnt"].mean())),
    ("Jam tersibuk (rata-rata)", f"{jam_rata.idxmax():02d}:00"),
    ("Jumlah hari", angka(len(day_f))),
]
for kolom, (label, nilai) in zip(st.columns(4), ringkasan):
    with kolom.container(border=True):
        st.metric(label, nilai)

tab_cuaca, tab_jam, tab_segmen = st.tabs(["Cuaca dan musim", "Pola per jam", "Segmentasi hari"])

# Tab 1: cuaca dan musim
with tab_cuaca:
    st.subheader("Seberapa besar cuaca dan musim memengaruhi penyewaan?")

    per_cuaca = day_f.groupby("cuaca", observed=True)["cnt"].agg(
        rata_rata="mean", total="sum", jumlah_hari="count"
    )
    kiri, kanan = st.columns(2)

    with kiri:
        fig, ax = plt.subplots(figsize=(6, 4.5))
        warna = [ABU] * len(per_cuaca)
        warna[int(per_cuaca["rata_rata"].to_numpy().argmin())] = AMBER
        batang = ax.bar(per_cuaca.index.astype(str), per_cuaca["rata_rata"], color=warna, width=0.6)
        ax.bar_label(batang, labels=[angka(v) for v in per_cuaca["rata_rata"]], padding=3)
        ax.set_title("Rata-rata penyewaan per hari menurut cuaca", loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("Kondisi cuaca")
        ax.set_ylabel("Rata-rata penyewaan per hari")
        ax.set_ylim(0, per_cuaca["rata_rata"].max() * 1.15)
        st.pyplot(fig)
        plt.close(fig)

    with kanan:
        musim_cuaca = day_f.groupby(["musim", "cuaca"], observed=True)["cnt"].mean().reset_index()
        urut_musim = [m for m in NAMA_MUSIM.values() if m in musim_dipilih]
        urut_cuaca = [c for c in NAMA_CUACA.values() if c in set(musim_cuaca["cuaca"])]
        fig, ax = plt.subplots(figsize=(6, 4.5))
        sns.barplot(
            data=musim_cuaca, x="musim", y="cnt", hue="cuaca",
            order=urut_musim, hue_order=urut_cuaca, palette=WARNA_CUACA, ax=ax,
        )
        ax.set_title("Rata-rata penyewaan per hari: musim dan cuaca", loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("Musim")
        ax.set_ylabel("Rata-rata penyewaan per hari")
        legenda_bawah(ax, "Cuaca", 3)
        st.pyplot(fig)
        plt.close(fig)

    terendah = per_cuaca["rata_rata"].idxmin()
    kalimat = (
        f"Rata-rata penyewaan terendah terjadi saat cuaca **{terendah}**, "
        f"yaitu {angka(per_cuaca.loc[terendah, 'rata_rata'])} per hari."
    )
    if "Cerah" in per_cuaca.index and terendah != "Cerah":
        turun = (1 - per_cuaca.loc[terendah, "rata_rata"] / per_cuaca.loc["Cerah", "rata_rata"]) * 100
        kalimat += f" Angka ini {turun:.0f}% lebih rendah daripada hari cerah."
    st.markdown(kalimat)

    sedikit = per_cuaca[per_cuaca["jumlah_hari"] < 30]
    if not sedikit.empty:
        nama = ", ".join(f"{k} ({v} hari)" for k, v in sedikit["jumlah_hari"].items())
        st.caption(f"Perhatian: jumlah hari yang tercatat sedikit untuk {nama}, jadi bacalah rata-ratanya dengan hati-hati.")

    with st.expander("Lihat tabel rata-rata dan total"):
        tabel = per_cuaca.rename(
            columns={"rata_rata": "Rata-rata per hari", "total": "Total penyewaan", "jumlah_hari": "Jumlah hari"}
        )
        st.dataframe(tabel.round(0).astype(int))
        pivot = day_f.pivot_table(index="musim", columns="cuaca", values="cnt", aggfunc="mean", observed=True)
        st.caption("Rata-rata penyewaan per hari menurut musim (baris) dan cuaca (kolom)")
        st.dataframe(pivot.round(0))

# Tab 2: pola per jam
with tab_jam:
    st.subheader("Kapan jam tersibuk, dan apakah berbeda di akhir pekan?")

    per_jam = hour_f.groupby(["tipe_hari", "hr"])["cnt"].mean().reset_index()
    kiri, kanan = st.columns([3, 2])

    with kiri:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        sns.lineplot(data=per_jam, x="hr", y="cnt", hue="tipe_hari", palette=WARNA_HARI, linewidth=2.4, ax=ax)
        for tipe, grup in per_jam.groupby("tipe_hari"):
            puncak = grup.loc[grup["cnt"].idxmax()]
            ax.scatter(puncak["hr"], puncak["cnt"], color=WARNA_HARI[tipe], zorder=5)
            ax.annotate(
                f"{int(puncak['hr']):02d}:00", (puncak["hr"], puncak["cnt"]),
                textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9,
            )
        ax.set_title("Rata-rata penyewaan per jam", loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("Jam (0-23)")
        ax.set_ylabel("Rata-rata penyewaan per jam")
        ax.set_xticks(range(0, 24, 2))
        ax.legend(title="Tipe hari", frameon=False)
        st.pyplot(fig)
        plt.close(fig)

    with kanan:
        per_segmen = hour_f.groupby(["tipe_hari", "segmen"], observed=True)["cnt"].mean().reset_index()
        fig, ax = plt.subplots(figsize=(5, 4.5))
        sns.barplot(
            data=per_segmen, x="segmen", y="cnt", hue="tipe_hari",
            order=SEGMEN, palette=WARNA_HARI, ax=ax,
        )
        ax.set_title("Rata-rata per jam menurut segmen waktu", loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("Segmen waktu")
        ax.set_ylabel("Rata-rata penyewaan per jam")
        plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
        legenda_bawah(ax, "Tipe hari", 2, jarak=-0.45)
        st.pyplot(fig)
        plt.close(fig)

    for tipe, grup in per_jam.groupby("tipe_hari"):
        atas, bawah = grup.loc[grup["cnt"].idxmax()], grup.loc[grup["cnt"].idxmin()]
        st.markdown(
            f"**{tipe}**: puncak pukul {int(atas['hr']):02d}:00 ({angka(atas['cnt'])} penyewaan per jam), "
            f"paling sepi pukul {int(bawah['hr']):02d}:00 ({angka(bawah['cnt'])})."
        )

# Tab 3: segmentasi hari (manual grouping)
with tab_segmen:
    st.subheader("Seperti apa sebaran hari sepi, normal, dan ramai?")
    st.caption(
        "Hari dikelompokkan secara manual menurut jumlah penyewaan harian: "
        "Sepi (sampai 3.000), Normal (3.001 sampai 6.000), Ramai (di atas 6.000)."
    )

    jumlah = day_f["kategori"].value_counts().reindex(KATEGORI).fillna(0)
    kiri, kanan = st.columns(2)

    with kiri:
        fig, ax = plt.subplots(figsize=(6, 4.5))
        warna = [ABU] * len(jumlah)
        warna[int(jumlah.to_numpy().argmax())] = TEAL
        batang = ax.bar(jumlah.index.astype(str), jumlah.values, color=warna, width=0.6)
        ax.bar_label(batang, labels=[angka(v) for v in jumlah.values], padding=3)
        ax.set_title("Jumlah hari menurut tingkat penyewaan", loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("Kategori hari")
        ax.set_ylabel("Jumlah hari")
        ax.set_ylim(0, jumlah.max() * 1.15)
        st.pyplot(fig)
        plt.close(fig)

    with kanan:
        urut_musim_tab3 = [m for m in NAMA_MUSIM.values() if m in musim_dipilih]
        komposisi = pd.crosstab(day_f["musim"], day_f["kategori"], normalize="index") * 100
        komposisi = komposisi.reindex(columns=KATEGORI).loc[urut_musim_tab3]
        fig, ax = plt.subplots(figsize=(6, 4.5))
        komposisi.plot(kind="barh", stacked=True, color=[ABU, TEAL, AMBER], width=0.6, ax=ax)
        for wadah, warna_teks in zip(ax.containers, [GELAP, "white", GELAP]):
            ax.bar_label(
                wadah, labels=[f"{v:.0f}%" if v >= 5 else "" for v in wadah.datavalues],
                label_type="center", fontsize=9, color=warna_teks,
            )
        ax.invert_yaxis()
        ax.set_title("Komposisi kategori hari per musim", loc="left", fontsize=12, fontweight="bold")
        ax.set_xlabel("Persentase hari")
        ax.set_ylabel("Musim")
        ax.legend(title="Kategori", frameon=False, bbox_to_anchor=(1, 1))
        st.pyplot(fig)
        plt.close(fig)

    dominan = jumlah.idxmax()
    st.markdown(
        f"Kategori yang paling sering muncul adalah **{dominan}**, yaitu {angka(jumlah[dominan])} dari "
        f"{angka(jumlah.sum())} hari ({jumlah[dominan] / jumlah.sum() * 100:.0f}%)."
    )

st.divider()
st.caption("Sumber data: Bike Sharing Dataset (2011-2012). Dibuat oleh Andini Putri Ahmawati.")