import pandas as pd
import os
import smtplib
import requests
import re
from email.mime.text import MIMEText
from datetime import datetime
from PyPDF2 import PdfReader

# === Konfigurasi ===
SHEET_FILE = "contracts.csv"  # Simulasi Google Sheets pakai CSV
STREAMLINE_URL = "https://api.streamline.ai/v1/contracts/review"  # Ganti dengan API asli

TELEGRAM_BOT_TOKEN = "8424327971:AAGsuuQEsDbSVHmbZXGprxnU-lROmKlNmFU"
TELEGRAM_CHAT_ID = "252191346"  # pastikan hasil getUpdates
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "poke.hunting62@gmail.com"
SMTP_PASS = "kydbjztpxetqcgoh"  # App Password Gmail


# === Helper Functions ===
def load_sheet():
    if os.path.exists(SHEET_FILE):
        return pd.read_csv(SHEET_FILE)
    return pd.DataFrame(columns=["ContractID", "FileName", "ExpiryDate", "UploadedAt"])


def save_sheet(df):
    df.to_csv(SHEET_FILE, index=False)


def streamline_review(file_path):
    """Upload file PDF ke API Streamline"""
    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(STREAMLINE_URL, files=files)

        print("Status:", response.status_code)
        print("Respon:", response.text[:300])

        # Jika API tidak mengembalikan JSON valid, kirim error
        try:
            return response.json()
        except Exception:
            return {"status": "error", "message": response.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)


def send_email(subject, body, to_email="framana01@gmail.com"):
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
    except Exception as e:
        print("Email error:", e)


def extract_expiry_from_pdf(file_path):
    """Extract expiry date (YYYY-MM-DD) dari isi PDF"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        match = re.search(r"\d{4}-\d{2}-\d{2}", text)
        if match:
            return match.group(0)
    except Exception as e:
        print("PDF parse error:", e)
    return None


def format_review_message(file_name, review_result):
    """Bikin pesan rapi untuk Telegram & Email"""
    if not isinstance(review_result, dict):
        return f"📄 Review Kontrak: {file_name}\n\nHasil: {review_result}"

    status = review_result.get("status", "Tidak diketahui")
    summary = review_result.get("review", review_result.get("message", "Tidak ada ringkasan"))

    if status == "error":
        return (
            f"📄 Review Kontrak: {file_name}\n"
            f"❌ ERROR: {summary}"
        )
    else:
        return (
            f"📄 Review Kontrak: {file_name}\n"
            f"✅ Status: {status}\n"
            f"📝 Ringkasan: {summary}"
        )


def add_contract(contract_id, file_path):
    df = load_sheet()
    file_name = os.path.basename(file_path)

    if contract_id in df["ContractID"].values:
        print("⚠️ Duplikasi kontrak, tidak disimpan:", contract_id)
        return False

    expiry_date = extract_expiry_from_pdf(file_path)
    if not expiry_date:
        print(f"⚠️ Tidak ditemukan tanggal expired di {file_name}, isi manual!")
        return False

    now = datetime.now().isoformat()
    new_row = {"ContractID": contract_id, "FileName": file_name, "ExpiryDate": expiry_date, "UploadedAt": now}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_sheet(df)
    print("✅ Kontrak berhasil disimpan:", file_name, "| Expiry:", expiry_date)

    # Jalankan review ke API Streamline
    review_result = streamline_review(file_path)
    print("Hasil Review:", review_result)

    # Format pesan review
    review_msg = format_review_message(file_name, review_result)

    # Kirim hasil review ke Telegram & Email
    send_telegram_message(review_msg)
    send_email(f"📄 Hasil Review Kontrak - {file_name}", review_msg)

    return True


def check_expired_contracts():
    df = load_sheet()
    if df.empty:
        print("Tidak ada kontrak di database.")
        return

    today = datetime.today()
    for _, row in df.iterrows():
        expiry = datetime.strptime(row["ExpiryDate"], "%Y-%m-%d")
        days_left = (expiry - today).days

        if days_left <= 90:
            msg_tg = f"⚠️ Peringatan Kontrak Segera Berakhir\nFile: {row['FileName']}\nTanggal Expired: {row['ExpiryDate']}\nSisa Waktu: {days_left} hari"
            msg_email = f"Halo Tim,\n\nKontrak berikut akan segera berakhir:\n\n📂 Nama File: {row['FileName']}\n📅 Tanggal Expired: {row['ExpiryDate']}\n⏳ Sisa Waktu: {days_left} hari\n\nMohon untuk melakukan review & tindak lanjut sebelum kontrak berakhir.\n\nSalam,\nSistem Monitoring Kontrak (Python)"

            send_telegram_message(msg_tg)
            send_email(f"⚠️ Kontrak Segera Expired - {row['FileName']}", msg_email)


# === Demo Run ===
if __name__ == "__main__":
    # Simulasi tambah kontrak (PDF harus ada di folder yang sama)
    add_contract("001", "kontrak_vendorA.pdf")
    add_contract("002", "kontrak_vendorB.pdf")
    add_contract("003", "kontrak_vendorC.pdf")

    # Cek kontrak yang mendekati expired
    check_expired_contracts()
