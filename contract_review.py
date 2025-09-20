import pandas as pd
import os
import smtplib
import requests
from email.mime.text import MIMEText
from datetime import datetime

# === Konfigurasi ===
SHEET_FILE = "contracts.csv"  # Simulasi Google Sheets pakai CSV
STREAMLINE_URL = "https://api.streamline.placeholder/review"
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "yourgmail@gmail.com"
SMTP_PASS = "your_app_password"


# === Helper Functions ===
def load_sheet():
    """Load sheet as dataframe"""
    if os.path.exists(SHEET_FILE):
        return pd.read_csv(SHEET_FILE)
    return pd.DataFrame(columns=["ContractID", "FileName", "ExpiryDate", "UploadedAt"])


def save_sheet(df):
    """Save dataframe back to CSV (simulate Google Sheets)"""
    df.to_csv(SHEET_FILE, index=False)


def streamline_review(file_name):
    """Simulate sending file to Streamline API"""
    try:
        response = requests.post(STREAMLINE_URL, json={"file": file_name})
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}


def send_telegram_message(message):
    """Send Telegram notification"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)


def send_email(subject, body, to_email="recipient@example.com"):
    """Send email via Gmail SMTP"""
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


def add_contract(contract_id, file_name, expiry_date):
    """Add new contract (skip if duplicate)"""
    df = load_sheet()

    # Cek duplikasi
    if contract_id in df["ContractID"].values:
        print("⚠️ Duplikasi kontrak, tidak disimpan:", contract_id)
        return False

    # Tambah kontrak baru
    now = datetime.now().isoformat()
    new_row = {"ContractID": contract_id, "FileName": file_name, "ExpiryDate": expiry_date, "UploadedAt": now}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_sheet(df)
    print("✅ Kontrak berhasil disimpan:", file_name)
    return True


def check_expired_contracts():
    """Check contracts that will expire <= 90 days"""
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
    # Simulasi tambah kontrak
    add_contract("001", "kontrak_vendorA.pdf", "2025-12-15")
    add_contract("002", "kontrak_vendorB.pdf", "2025-10-05")
    add_contract("003", "kontrak_vendorC.pdf", "2026-01-01")

    # Cek kontrak yang mendekati expired
    check_expired_contracts()
