import streamlit as st
import pandas as pd
import os
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- Page Config ---
st.set_page_config(page_title="Invoice Tracker", layout="wide")
st.title("📊 Invoice Tracker Dashboard")

# --- Folders and Files ---
DATA_FOLDER = "data"
os.makedirs(DATA_FOLDER, exist_ok=True)
DATA_FILE = os.path.join(DATA_FOLDER, "last_uploaded.xlsx")
TIME_FILE = os.path.join(DATA_FOLDER, "upload_time.txt")
CREDENTIALS_FILE = os.path.join(DATA_FOLDER, "sender_credentials.txt")

# change by sid

sender_email = st.secrets["sender_email"]
sender_password = st.secrets["sender_password"]


# --- Session State Defaults ---
if "sender_email" not in st.session_state:
    st.session_state.sender_email = ""
if "sender_password" not in st.session_state:
    st.session_state.sender_password = ""
if "show_sender_modal" not in st.session_state:
    st.session_state.show_sender_modal = False
if "approver_action" not in st.session_state:
    st.session_state.approver_action = None

# --- Load Sender Credentials if exist ---
if os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE, "r") as f:
        lines = f.read().splitlines()
        if len(lines) >= 2:
            st.session_state.sender_email = lines[0]
            st.session_state.sender_password = lines[1]

# --- Top-right key icon for credentials ---
col1, col2, col3 = st.columns([0.95, 0.02, 0.03])
with col3:
    if st.button("🔑"):
        st.session_state.show_sender_modal = not st.session_state.show_sender_modal

if st.session_state.show_sender_modal:
    with st.container():
        st.markdown("<div style='width:auto; max-width:400px; padding:10px; border:1px solid #ddd; border-radius:8px;'>", unsafe_allow_html=True)
        sender_email_input = st.text_input("Sender Email (your company)", st.session_state.sender_email)
        sender_password_input = st.text_input("Password / App Password", st.session_state.sender_password, type="password")
        col_save, col_close = st.columns(2)
        with col_save:
            if st.button("💾 Save Credentials", key="save_credentials"):
                st.session_state.sender_email = sender_email_input
                st.session_state.sender_password = sender_password_input
                with open(CREDENTIALS_FILE, "w") as f:
                    f.write(f"{sender_email_input}\n{sender_password_input}")
                st.success("✅ Sender credentials saved!")
        with col_close:
            if st.button("❌ Close", key="close_credentials"):
                st.session_state.show_sender_modal = False
        st.markdown("</div>", unsafe_allow_html=True)

# --- Email Sending Function ---
def send_email(sender_email, sender_password, to_email, subject, body, cc=None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email
    if cc:
        msg['Cc'] = cc
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        return True, "Email sent successfully!"
    except Exception as e:
        return False, str(e)

# --- Load Excel Data ---
if os.path.exists(DATA_FILE):
    df = pd.read_excel(DATA_FILE)
    st.session_state.stored_data = df
    if os.path.exists(TIME_FILE):
        with open(TIME_FILE, "r") as f:
            st.session_state.last_uploaded_time = f.read().strip()
else:
    st.session_state.stored_data = None
    st.session_state.last_uploaded_time = None

uploaded_file = st.file_uploader("📤 Upload New Excel File", type=["xlsx", "xls"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.session_state.stored_data = df
    df.to_excel(DATA_FILE, index=False)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(TIME_FILE, "w") as f:
        f.write(current_time)
    st.session_state.last_uploaded_time = current_time
    st.success("✅ File uploaded and saved successfully!")

# --- Refresh Button ---
if st.button("🔄 Refresh Data"):
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE)
        st.session_state.stored_data = df
        st.success("✅ Data refreshed successfully!")
    else:
        st.warning("⚠️ No saved file found to refresh!")

# --- Main Dashboard ---
if st.session_state.stored_data is not None:
    df = st.session_state.stored_data.copy()

    # Columns
    paid_col = next((col for col in df.columns if "status" in col.lower() or "payment" in col.lower()), None)
    amount_col = next((col for col in df.columns if "amount" in col.lower() or "total" in col.lower() or "due" in col.lower()), None)
    date_col = next((col for col in df.columns if "date" in col.lower() or "raised" in col.lower()), None)
    client_col = next((col for col in df.columns if "client name" in col.lower()), None)  # Using client mail as client_col
    approver_mail_col = next((col for col in df.columns if "approver mail" in col.lower()), None)
    client_mail_col = next((col for col in df.columns if "client mail" in col.lower()), None)
    cc_mail_col = next((col for col in df.columns if "cc" in col.lower()), None)
    invoice_col = next((col for col in df.columns if "invoice" in col.lower() and ("no" in col.lower() or "number" in col.lower() or "id" in col.lower())), None)

    # Filter by client
    client_options = ["All Clients"] + sorted(df[client_col].dropna().unique().tolist()) if client_col else ["All Clients"]
    selected_client = st.selectbox("Select Client", client_options)
    df_filtered = df[df[client_col] == selected_client] if selected_client != "All Clients" else df.copy()

    # Metrics
    if paid_col:
        paid_df = df_filtered[df_filtered[paid_col].astype(str).str.lower().str.contains("paid")]
        unpaid_df = df_filtered[~df_filtered[paid_col].astype(str).str.lower().str.contains("paid")]
    else:
        paid_df = pd.DataFrame()
        unpaid_df = df_filtered

    st.markdown("### 📈 Dashboard Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🧾 Total Clients", df[client_col].nunique() if client_col else len(df))
    col2.metric("📄 Total Invoices", len(df_filtered))
    col3.metric("✅ Paid", len(paid_df))
    col4.metric("⚠️ Pending", len(unpaid_df))
    col5.metric("💰 Total Due", unpaid_df[amount_col].sum() if amount_col else 0)

    # --- Ageing Table & Graph ---
    if unpaid_df.shape[0] > 0 and date_col:
        ageing_df = unpaid_df.copy()
        ageing_df[date_col] = pd.to_datetime(ageing_df[date_col], errors="coerce")
        ageing_df["Days Pending"] = (datetime.now() - ageing_df[date_col]).dt.days

        # Display table
        st.markdown("### ⏳ Ageing Table")
        st.dataframe(ageing_df[[client_col, invoice_col, amount_col, date_col, "Days Pending"]])

        # Display bar chart
        st.markdown("### 📊 Ageing Graph")
        chart_df = ageing_df.copy()
        chart_df[invoice_col] = chart_df[invoice_col].astype(str)  # Ensure invoice numbers are strings
        st.bar_chart(data=chart_df.set_index(invoice_col)["Days Pending"])

# --- Email Actions Sidebar ---
if client_col and st.session_state.stored_data is not None:
    st.sidebar.markdown("### 📧 Email Actions")
    selected_client_name = st.sidebar.selectbox(
        "Select Client for Email",
        sorted(df[client_col].dropna().unique().tolist())
    )
    client_invoices = df[df[client_col] == selected_client_name]

    # Unpaid invoices
    unpaid_invoices = client_invoices[
        ~client_invoices[paid_col].astype(str).str.lower().str.contains("paid")
    ] if paid_col else client_invoices
    num_unpaid = len(unpaid_invoices)
    total_due = unpaid_invoices[amount_col].sum() if amount_col and num_unpaid > 0 else 0

    # Build a neatly formatted HTML email
    invoice_rows = ""
    for idx, row in unpaid_invoices.iterrows():
        invoice_num = row[invoice_col] if invoice_col else row.name + 1
        amount_val = f"${row[amount_col]:,.2f}" if amount_col else "N/A"
        invoice_date_val = row[date_col].strftime("%Y-%m-%d") if date_col else "N/A"
        days_pending = (datetime.now() - pd.to_datetime(row[date_col], errors='coerce')).days if date_col else "N/A"

        invoice_rows += f"""
        <tr>
            <td>{invoice_num}</td>
            <td>{amount_val}</td>
            <td>{invoice_date_val}</td>
            <td>{days_pending} days</td>
        </tr>
        """

    auto_message = f"""
    <html>
    <body>
    <p>Dear {selected_client_name},</p>
    <p>Please find below your pending invoices:</p>
    <table border="1" cellpadding="5" cellspacing="0">
        <thead>
            <tr>
                <th>Invoice #</th>
                <th>Amount</th>
                <th>Invoice Date</th>
                <th>Days Pending</th>
            </tr>
        </thead>
        <tbody>
            {invoice_rows}
        </tbody>
    </table>
    <p><strong>Total Invoices Pending:</strong> {num_unpaid}<br>
    <strong>Total Amount Due:</strong> ${total_due:,.2f}</p>
    <p>Kindly arrange the payments at the earliest.</p>
    <p>Thanks!</p>
    </body>
    </html>
    """

    email_subject = "Pending Invoice Payments | S2 Integrators"
    st.sidebar.text_input("Email Subject", value=email_subject, key="email_subject")
    st.sidebar.text_area("Email Message (HTML)", value=auto_message, height=300, key="email_message")

    client_email = client_invoices[client_mail_col].iloc[0] if client_mail_col else None
    cc_email = client_invoices[cc_mail_col].iloc[0] if cc_mail_col else None

    st.sidebar.markdown("### 📨 Send to Client")
    if st.sidebar.button("📤 Send Email to Client"):
        if not st.session_state.sender_email or not st.session_state.sender_password:
            st.sidebar.warning("⚠️ Please set sender credentials!")
        elif client_email:
            # Modify send_email to handle HTML content
            def send_email_html(sender_email, sender_password, to_email, subject, html_body, cc=None):
                msg = EmailMessage()
                msg['Subject'] = subject
                msg['From'] = sender_email
                msg['To'] = to_email
                if cc:
                    msg['Cc'] = cc
                msg.add_alternative(html_body, subtype='html')
                try:
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                        smtp.login(sender_email, sender_password)
                        smtp.send_message(msg)
                    return True, "Email sent successfully!"
                except Exception as e:
                    return False, str(e)

            success, msg = send_email_html(
                st.session_state.sender_email,
                st.session_state.sender_password,
                client_email,
                st.session_state.email_subject,
                st.session_state.email_message,
                cc=cc_email
            )
            if success:
                st.sidebar.success(f"✅ Email sent to {client_email}")
            else:
                st.sidebar.error(f"❌ Failed to send email: {msg}")
# 

