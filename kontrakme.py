import streamlit as st
import openai
from PyPDF2 import PdfReader
import io

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(page_title="Penganalisis Kontrak PDF dengan OpenAI", layout="wide")

st.title("Penganalisis Dokumen Kontrak PDF")
st.write("Unggah dokumen kontrak Anda dan dapatkan analisis dari OpenAI.")

# --- Sidebar untuk API Key ---
with st.sidebar:
    st.header("Konfigurasi OpenAI")
    openai_api_key = st.text_input("Masukkan OpenAI API Key Anda", type="password")
    st.warning("API Key Anda tidak akan disimpan.")

    st.markdown("---")
    st.header("Petunjuk")
    st.markdown("""
    1. Masukkan OpenAI API Key Anda di atas.
    2. Unggah file PDF dokumen kontrak Anda.
    3. Klik 'Analisis Kontrak' untuk memulai.
    4. Tunggu hasilnya di bawah.
    """)

# --- Fungsi untuk Mengekstrak Teks dari PDF ---
def extract_text_from_pdf(uploaded_file):
    pdf_reader = PdfReader(uploaded_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or "" # Handle potential None for empty pages
    return text

# --- Fungsi untuk Menganalisis Teks dengan OpenAI ---
def analyze_contract_with_openai(contract_text, api_key):
    if not api_key:
        st.error("Harap masukkan OpenAI API Key Anda di sidebar.")
        return "API Key tidak tersedia."

    openai.api_key = api_key

    # Batasi ukuran input ke model jika terlalu panjang
    # Model GPT-3.5 Turbo memiliki batasan token, jadi kita perlu berhati-hati
    max_tokens_per_prompt = 15000 # Contoh batas token untuk input
    if len(contract_text) > max_tokens_per_prompt * 4: # Estimasi kasar karakter per token
        contract_text = contract_text[:max_tokens_per_prompt * 4]
        st.warning(f"Dokumen terlalu panjang, hanya {max_tokens_per_prompt * 4} karakter pertama yang akan dianalisis.")

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # Anda bisa coba "gpt-4" jika memiliki akses
            messages=[
                {"role": "system", "content": "Anda adalah asisten yang ahli dalam menganalisis dokumen kontrak. Berikan ringkasan, poin-poin penting, potensi risiko, dan klausul kunci."},
                {"role": "user", "content": f"Harap analisis dokumen kontrak berikut dan berikan poin-poin penting, potensi risiko, dan klausul kunci. Juga, ringkaslah inti kontrak. \n\nKontrak:\n{contract_text}"}
            ],
            temperature=0.7,
            max_tokens=1000 # Batasi panjang respons dari model
        )
        return response.choices[0].message.content
    except openai.AuthenticationError:
        st.error("OpenAI API Key tidak valid. Harap periksa kembali.")
        return "Kesalahan Autentikasi API."
    except openai.APIError as e:
        st.error(f"Terjadi kesalahan API OpenAI: {e}")
        return f"Kesalahan API: {e}"
    except Exception as e:
        st.error(f"Terjadi kesalahan tak terduga: {e}")
        return f"Kesalahan: {e}"

# --- Main Konten Aplikasi ---
uploaded_file = st.file_uploader("Unggah dokumen kontrak PDF Anda", type="pdf")

if uploaded_file is not None:
    st.success("File PDF berhasil diunggah!")

    # Tampilkan nama file
    st.write(f"Nama file: {uploaded_file.name}")

    if st.button("Analisis Kontrak", type="primary"):
        if openai_api_key:
            with st.spinner("Mengekstrak teks dari PDF..."):
                contract_text = extract_text_from_pdf(uploaded_file)
                st.subheader("Teks yang Diekstrak (Pratinjau)")
                st.expander("Klik untuk melihat teks yang diekstrak").text_area("Teks", contract_text[:1000] + "..." if len(contract_text) > 1000 else contract_text, height=200)


            if contract_text:
                with st.spinner("Menganalisis kontrak dengan OpenAI... Ini mungkin membutuhkan waktu beberapa saat."):
                    analysis_result = analyze_contract_with_openai(contract_text, openai_api_key)
                    st.subheader("Hasil Analisis Kontrak:")
                    st.markdown(analysis_result)
            else:
                st.error("Tidak dapat mengekstrak teks dari PDF. Pastikan PDF tidak kosong atau terenkripsi.")
        else:
            st.error("Harap masukkan OpenAI API Key Anda di sidebar sebelum menganalisis.")
