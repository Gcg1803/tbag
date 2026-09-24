#!/usr/bin/env python3
import subprocess
import re
import time

BASLIK = "Android Cihaz Bağlantısı"
TCPIP_PORT = 5555
MAX_SIZE = "1280"
VIDEO_BITRATE = "2M"
MAX_FPS = "30"


def adb(*args, timeout=15):
    try:
        sonuc = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
        return sonuc.returncode, sonuc.stdout.strip()
    except Exception:
        return 1, ""


def bilgi_goster(mesaj, tur="info"):
    subprocess.run(["zenity", f"--{tur}", "--title", BASLIK, "--text", mesaj, "--width", "360"], capture_output=True)


def tek_tik_secim(mesaj, secenek_1, secenek_2):
    sonuc = subprocess.run(
        ["zenity", "--question", "--title", BASLIK, "--text", mesaj,
         "--extra-button", secenek_1, "--extra-button", secenek_2, "--cancel-label=Vazgeç"],
        capture_output=True, text=True)
    secim = sonuc.stdout.strip()
    return secim if secim in (secenek_1, secenek_2) else None


def usb_cihaz_bekle(sure_sn=30):
    for _ in range(sure_sn):
        _, cikti = adb("devices")
        for satir in cikti.splitlines()[1:]:
            parcalar = satir.split()
            if len(parcalar) == 2 and parcalar[1] == "device" and ":" not in parcalar[0]:
                return parcalar[0]
        time.sleep(1)
    return None


def tablet_wifi_ip_al(usb_seri):
    for komut in (["-s", usb_seri, "shell", "ip", "route", "show", "dev", "wlan0"],
                  ["-s", usb_seri, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"]):
        _, cikti = adb(*komut)
        eslesme = re.search(r"(?:src|inet) (\d{1,3}(?:\.\d{1,3}){3})", cikti)
        if eslesme:
            return eslesme.group(1)
    return None


def adb_baglanti_dogrula(serial, deneme=5):
    for _ in range(deneme):
        _, cikti = adb("devices")
        for satir in cikti.splitlines()[1:]:
            if satir.startswith(serial) and "device" in satir:
                return True
        time.sleep(1)
    return False


def kablolu_baglan():
    usb_seri = usb_cihaz_bekle()
    if not usb_seri:
        bilgi_goster("USB üzerinden bir cihaz bulunamadı.\nKabloyu kontrol edin ve USB hata ayıklamanın açık olduğundan emin olun.", "error")
        return None

    ip = tablet_wifi_ip_al(usb_seri)
    if not ip:
        bilgi_goster("Tabletin Wi-Fi adresi okunamadı.\nTabletin Wi-Fi'a bağlı olduğundan emin olun.", "error")
        return None

    adb("-s", usb_seri, "tcpip", str(TCPIP_PORT))
    time.sleep(2)

    serial = f"{ip}:{TCPIP_PORT}"
    adb("connect", serial)

    if not adb_baglanti_dogrula(serial):
        bilgi_goster("Cihaza bağlanılamadı.", "error")
        return None
    return serial


def kirpma_hesapla(genislik, yukseklik):
    if genislik >= yukseklik:
        if genislik / yukseklik > 16 / 9:
            h, w = yukseklik, int(yukseklik * 16 / 9)
            x, y = (genislik - w) // 2, 0
        else:
            w, h = genislik, int(genislik * 9 / 16)
            x, y = 0, (yukseklik - h) // 2
    else:
        if yukseklik / genislik > 16 / 9:
            w, h = genislik, int(genislik * 16 / 9)
            x, y = 0, (yukseklik - h) // 2
        else:
            h, w = yukseklik, int(yukseklik * 9 / 16)
            x, y = (genislik - w) // 2, 0
    w, h, x, y = (v - v % 2 for v in (w, h, x, y))
    return w, h, x, y


def ekran_orani_sor():
    secim = tek_tik_secim("Görüntü tahtada nasıl gösterilsin?", "Tabletin Kendi Oranı", "Tahtaya Tam Sığdır")
    if secim is None:
        return None
    return secim == "Tahtaya Tam Sığdır"


def scrcpy_baslat(serial, tam_sigdir):
    crop_param = []
    if tam_sigdir:
        _, cikti = adb("-s", serial, "shell", "wm", "size")
        eslesme = re.search(r"(\d+)x(\d+)", cikti)
        if eslesme:
            genislik, yukseklik = int(eslesme.group(1)), int(eslesme.group(2))
            w, h, x, y = kirpma_hesapla(genislik, yukseklik)
            crop_param = ["--crop", f"{w}:{h}:{x}:{y}"]
        else:
            bilgi_goster("Çözünürlük okunamadı, kırpma uygulanmadan devam ediliyor.", "warning")

    subprocess.run(["scrcpy", "-s", serial, "--max-size", MAX_SIZE, "--video-bit-rate", VIDEO_BITRATE,
                     "--max-fps", MAX_FPS, "-f", *crop_param])


def main():
    subprocess.run(["adb", "disconnect"], capture_output=True)

    serial = kablolu_baglan()
    if serial is None:
        return

    tam_sigdir = ekran_orani_sor()
    if tam_sigdir is None:
        return

    scrcpy_baslat(serial, tam_sigdir)


if __name__ == "__main__":
    main()
