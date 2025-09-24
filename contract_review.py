import streamlit as st
import pandas as pd
import os
from datetime import datetime
from PyPDF2 import PdfReader
import re
import requests
import smtplib
from email.mime.text import MIMEText

# === Konfigurasi ===
SHEET_FILE = "contracts.csv"
STREAMLINE_URL = "https://api.streamline.ai/v1/contracts/review"

# Secrets disimpan di Streamlit Cloud
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "8424327971:AAGsuuQEsDbSVHmbZXGprxnU-lROmKlNmFU")
TELEGRAM_CHAT_ID = st.secrets.get("TELEGRAM_CHAT_ID", "252191346")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = st.secrets.get("SMTP_USER", "poke.hunting62@gmail.com")
SMTP_PASS = st.secrets.get("SMTP_PASS", "kydbjztpxetqcgoh")# App Password Gmail
EMAIL_TO = st.secrets.get("EMAIL_TO", "ombaiakas62@gmail.com")

os.makedirs("uploads", exist_ok=True)


# === Helper Functions ===
def load_sheet():
    if os.path.exists(SHEET_FILE):
        return pd.read_csv(SHEET_FILE)
    return pd.DataFrame(columns=["ContractID","FileName","ExpiryDate","UploadedAt"])

def save_sheet(df):
    df.to_csv(SHEET_FILE, index=False)

def extract_expiry_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        match = re.search(r"\d{4}-\d{2}-\d{2}", text)
        if match:
            return match.group(0)
    except Exception:
        return None
    return None

def streamline_review(file_path):
    try:
        with open(file_path,"rb") as f:
            files={"file":f}
            response=requests.post(STREAMLINE_URL,files=files)
        return response.json()
    except Exception as e:
        return {"status":"error","message":str(e)}

def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot8424327971:AAGsuuQEsDbSVHmbZXGprxnU-lROmKlNmFU/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        st.error(f"Telegram error: {e}")

def send_email(subject, body, to_email=EMAIL_TO):
    if not SMTP_USER or not SMTP_PASS or not EMAIL_TO:
        return
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
        st.error(f"Email error: {e}")

def format_review_message(file_name, review_result):
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


# === Streamlit UI ===
st.title("📄 Sistem Monitoring Kontrak")

menu = st.sidebar.selectbox("Menu", ["Tambah Kontrak", "Daftar Kontrak", "Cek Kontrak Expired"])

if menu == "Tambah Kontrak":
    st.header("Upload Kontrak Baru")
    contract_id = st.text_input("Contract ID")
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded_file and contract_id and st.button("Simpan & Review"):
        file_path = os.path.join("uploads", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        expiry = extract_expiry_from_pdf(file_path)
        if expiry:
            df = load_sheet()
            now = datetime.now().isoformat()
            new_row = {"ContractID": contract_id,"FileName": uploaded_file.name,
                       "ExpiryDate": expiry,"UploadedAt": now}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_sheet(df)

            st.success(f"✅ Kontrak {uploaded_file.name} berhasil disimpan, Expiry: {expiry}")

            # Jalankan review API
            result = streamline_review(file_path)
            st.subheader("📊 Hasil Review dari Streamline")
            st.json(result)

            # Format & kirim notifikasi
            review_msg = format_review_message(uploaded_file.name, result)
            send_telegram_message(review_msg)
            send_email(f"📄 Hasil Review Kontrak - {uploaded_file.name}", review_msg)

            st.info("📬 Hasil review juga dikirim ke Telegram & Email (jika secrets sudah diisi).")
        else:
            st.error("❌ Tanggal expired tidak ditemukan di PDF")

elif menu == "Daftar Kontrak":
    st.header("Daftar Kontrak")
    df = load_sheet()
    if df.empty:
        st.info("Belum ada kontrak.")
    else:
        st.dataframe(df)

elif menu == "Cek Kontrak Expired":
    st.header("Kontrak yang Akan Expired (<90 hari)")
    df = load_sheet()
    if df.empty:
        st.info("Belum ada kontrak.")
    else:
        today = datetime.today()
        expired_df = []
        for _, row in df.iterrows():
            expiry = datetime.strptime(row["ExpiryDate"], "%Y-%m-%d")
            days_left = (expiry - today).days
            if days_left <= 90:
                expired_df.append({**row, "DaysLeft": days_left})
        if expired_df:
            st.dataframe(pd.DataFrame(expired_df))
        else:
            st.success("✅ Tidak ada kontrak yang akan expired dalam 90 hari.")
