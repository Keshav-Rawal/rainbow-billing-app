import streamlit as st
import extra_streamlit_components as stx
import time
import pandas as pd
from weasyprint import HTML
from num2words import num2words
import datetime
import mysql.connector
import json
import uuid

st.set_page_config(page_title="Rainbow ERP - Pro SaaS", layout="wide")

# ==========================================
# 1. SAFE DATABASE FUNCTIONS
# ==========================================
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        connect_timeout=10,
        use_pure=True
    )

def init_db():
    if "db_initialized" not in st.session_state:
        try:
            conn = get_connection(); cursor = conn.cursor()
            
            cursor.execute("CREATE TABLE IF NOT EXISTS users (uid VARCHAR(50) PRIMARY KEY, password VARCHAR(50) NOT NULL, role VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS company_profiles (uid VARCHAR(50) PRIMARY KEY, name VARCHAR(100) NOT NULL, gstin VARCHAR(50), address TEXT, state VARCHAR(50), state_code VARCHAR(20), tagline VARCHAR(200), contact VARCHAR(200), manufacturing VARCHAR(255))")
            
            # Challans Table
            cursor.execute("CREATE TABLE IF NOT EXISTS challans (id INT AUTO_INCREMENT PRIMARY KEY, created_by VARCHAR(100), challan_date VARCHAR(20), challan_no VARCHAR(50), party_name VARCHAR(100), party_address TEXT, party_gstin VARCHAR(50), party_state VARCHAR(50), party_state_code VARCHAR(20), vehicle_no VARCHAR(50), date_of_supply VARCHAR(20), transport_mode VARCHAR(50), place_of_supply VARCHAR(100), items_data TEXT, amount VARCHAR(50), is_deleted INT DEFAULT 0, deleted_at DATETIME NULL)")
            
            # Tax Invoices Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tax_invoices (
                    id INT AUTO_INCREMENT PRIMARY KEY, created_by VARCHAR(100), invoice_date VARCHAR(20), invoice_no VARCHAR(50), vendor_code VARCHAR(50), po_no VARCHAR(50), po_date VARCHAR(20), bill_to_name VARCHAR(100), bill_to_address TEXT, bill_to_gstin VARCHAR(50), bill_to_state VARCHAR(50), bill_to_state_code VARCHAR(20), ship_to_name VARCHAR(100), ship_to_address TEXT, ship_to_gstin VARCHAR(50), ship_to_state VARCHAR(50), ship_to_state_code VARCHAR(20), transport_mode VARCHAR(50), vehicle_no VARCHAR(50), date_of_supply VARCHAR(50), place_of_supply VARCHAR(100), items_data TEXT, amount VARCHAR(50), tax_type VARCHAR(20), is_deleted INT DEFAULT 0, deleted_at DATETIME NULL
                )
            """)
            
            # --- 30 DAY AUTO-CLEANUP ---
            try: cursor.execute("DELETE FROM challans WHERE is_deleted = 1 AND deleted_at < NOW() - INTERVAL 30 DAY")
            except: pass
            try: cursor.execute("DELETE FROM tax_invoices WHERE is_deleted = 1 AND deleted_at < NOW() - INTERVAL 30 DAY")
            except: pass

            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0: cursor.execute("INSERT INTO users (uid, password, role, name) VALUES (%s, %s, %s, %s)", ("boss", "admin123", "superadmin", "Keshav (Master)"))
            conn.commit(); cursor.close(); conn.close()
            st.session_state.db_initialized = True
        except: pass

init_db()

def fetch_data(query, params=None):
    try:
        conn = get_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ()); data = cursor.fetchall()
        cursor.close(); conn.close(); return data
    except: return []

def execute_data(query, params):
    try:
        conn = get_connection(); cursor = conn.cursor()
        cursor.execute(query, params); conn.commit()
        cursor.close(); conn.close(); return True
    except: return False

def get_company_profile(uid):
    data = fetch_data("SELECT * FROM company_profiles WHERE uid = %s", (uid,))
    return data[0] if data else {"name": "RAINBOW INDUSTRIES", "gstin": "09AAAAA0000A1Z1", "address": "2804, Dhoom Manikpur, Dadri (G.B. Nagar) U.P. 203207", "state": "UP", "state_code": "09", "tagline": "AN ISO 9001:2015 Certified Company", "contact": "E Mail Id: rainbowindustries647@gmail.com", "manufacturing": "Manufactures of: Plastic Components, Automobiles, Electricals & Electronics."}

def parse_date(date_str):
    if date_str:
        try: return datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
        except: pass
    return datetime.date.today()

# ==========================================
# 2. SESSION & AUTH MANAGER
# ==========================================
cookie_manager = stx.CookieManager(key="cookie_manager")
time.sleep(0.1)

if "auth_logged_in" not in st.session_state:
    try: 
        if cookie_manager.get(cookie="rainbow_erp_auth") == "verified":
            st.session_state.update({"auth_logged_in": True, "auth_role": cookie_manager.get(cookie="rainbow_user_role"), "auth_name": cookie_manager.get(cookie="rainbow_user_name"), "auth_uid": cookie_manager.get(cookie="rainbow_user_uid")})
    except: st.session_state.auth_logged_in = False

if "cust_menu" not in st.session_state: st.session_state.cust_menu = "📝 Delivery Challan"

# ==========================================
# 3. HTML GENERATOR FOR TAX INVOICE
# ==========================================
def generate_tax_invoice_html(comp, fd, items, tax_type, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, copy_title):
    items_html = ""
    for idx, item in enumerate(items):
        qty_display = f"{item['qty']} Pcs" if item['qty'] > 0 else ""
        items_html += f"<tr><td style='text-align:center;'>{idx+1}.</td><td><strong>{item['desc'].replace(chr(10), '<br>')}</strong></td><td style='text-align:center;'>{item.get('hsn','')}</td><td style='text-align:center;'>{item.get('boxes','')}</td><td style='text-align:center;'>{qty_display}</td><td style='text-align:right;'>{item['rate']:.2f}</td><td style='text-align:right;'>{item['amount']:.2f}</td></tr>"
    
    tax_rows = ""
    if tax_type == "IGST":
        tax_rows = f"<tr><td style='text-align:right; font-weight:bold; background-color:#f8f9fa;'>Add: IGST @ 18%</td><td style='text-align:right;'>{igst:.2f}</td></tr>"
    else:
        tax_rows = f"<tr><td style='text-align:right; font-weight:bold; background-color:#f8f9fa;'>Add: CGST @ 9%</td><td style='text-align:right;'>{cgst:.2f}</td></tr><tr><td style='text-align:right; font-weight:bold; background-color:#f8f9fa;'>Add: SGST @ 9%</td><td style='text-align:right;'>{sgst:.2f}</td></tr>"
        
    return f"""
    <div class="page-container">
        <div class="top-label">{copy_title}</div>
        <div class="container">
            <div class="header">
                <div class="header-left"><strong>GSTIN :</strong> {comp['gstin']}<br><strong>State :</strong> {comp['state']} &nbsp; <strong>Code :</strong> {comp['state_code']}</div>
                <div class="header-right"><strong>M. No. :</strong> {comp['contact'].split('Mob.:')[-1].split('|')[0].strip() if 'Mob.:' in comp['contact'] else '9711325563'}</div>
                <h2 style="margin: 0; font-size: 16px; text-decoration: underline;">TAX INVOICE</h2>
                <h1 style="color: #1a4f8b; font-size: 32px; font-weight: 900; margin: 10px 0 5px 0;">{comp['name']}</h1>
                <p style="font-weight: bold; margin: 2px 0;">{comp['tagline']}</p>
                <p style="margin: 2px 0;">{comp['address']}</p>
                <p style="margin: 2px 0; font-weight: bold;">{comp['contact']}</p>
                <p style="margin: 5px 0 0 0; font-weight: bold; font-style: italic; color: #1a4f8b;">{comp['manufacturing']}</p>
            </div>
            <table class="info-table">
                <tr>
                    <td style="width: 50%;">
                        <table style="border:none; width:100%;">
                            <tr><td style="border:none; padding:4px;"><strong>Invoice No.</strong></td><td style="border:none; padding:4px;">: <strong>{fd.get('invoice_no','')}</strong></td></tr>
                            <tr><td style="border:none; padding:4px;"><strong>Invoice Date</strong></td><td style="border:none; padding:4px;">: {fd.get('invoice_date','')}</td></tr>
                            <tr><td style="border:none; padding:4px;"><strong>Vendor Code</strong></td><td style="border:none; padding:4px;">: {fd.get('vendor_code','')}</td></tr>
                            <tr><td style="border:none; padding:4px;"><strong>P. O. No.</strong></td><td style="border:none; padding:4px;">: {fd.get('po_no','')}</td></tr>
                            <tr><td style="border:none; padding:4px;"><strong>P. O. Date</strong></td><td style="border:none; padding:4px;">: {fd.get('po_date','')}</td></tr>
                        </table>
                    </td>
                    <td style="width: 50%;">
                        <table style="border:none; width:100%;">
                            <tr><td style="border:none; padding:4px;"><strong>Transportation Mode</strong></td><td style="border:none; padding:4px;">: {fd.get('transport_mode','Road')}</td></tr>
                            <tr><td style="border:none; padding:4px;"><strong>Vehicle Number</strong></td><td style="border:none; padding:4px;">: {fd.get('vehicle_no','')}</td></tr>
                            <tr><td style="border:none; padding:4px;"><strong>Date & Time of Supply</strong></td><td style="border:none; padding:4px;">: {fd.get('date_of_supply','')}</td></tr>
                            <tr><td style="border:none; padding:4px;"><strong>Place of Supply</strong></td><td style="border:none; padding:4px;">: {fd.get('place_of_supply','')}</td></tr>
                        </table>
                    </td>
                </tr>
            </table>
            <table class="info-table" style="border-top: none;">
                <tr>
                    <td style="width: 50%; text-align: center; background-color: #f0f0f0; font-weight: bold;">Bill to Party :</td>
                    <td style="width: 50%; text-align: center; background-color: #f0f0f0; font-weight: bold;">Details of Consignee / Shipped to :</td>
                </tr>
                <tr>
                    <td style="vertical-align: top;">
                        <strong>Name :</strong> {fd.get('bill_to_name','')}<br>
                        <strong>Address :</strong> {fd.get('bill_to_address','').replace(chr(10), '<br>')}<br><br>
                        <strong>GSTIN :</strong> {fd.get('bill_to_gstin','')}<br>
                        <strong>State :</strong> {fd.get('bill_to_state','')} &nbsp;&nbsp;&nbsp;&nbsp; <strong>State Code :</strong> {fd.get('bill_to_state_code','')}
                    </td>
                    <td style="vertical-align: top;">
                        <strong>Name :</strong> {fd.get('ship_to_name','')}<br>
                        <strong>Address :</strong> {fd.get('ship_to_address','').replace(chr(10), '<br>')}<br><br>
                        <strong>GSTIN :</strong> {fd.get('ship_to_gstin','')}<br>
                        <strong>State :</strong> {fd.get('ship_to_state','')} &nbsp;&nbsp;&nbsp;&nbsp; <strong>State Code :</strong> {fd.get('ship_to_state_code','')}
                    </td>
                </tr>
            </table>
            <table class="items-table">
                <tr>
                    <th style="width:5%;">Sr.<br>No.</th><th style="width:40%;">Product Description</th><th style="width:10%;">HSN<br>Code</th><th style="width:10%;">No. & Description<br>of Package</th><th style="width:10%;">Qty.</th><th style="width:10%;">Rate</th><th style="width:15%;">Taxable Amount</th>
                </tr>
                {items_html}
                <tr class="spacer-row"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
            </table>
            <table style="border-top: 2px solid #1c2d42; width: 100%; border-collapse: collapse;">
                <tr>
                    <td rowspan="5" style="width:65%; padding: 10px; border-right: 2px solid #1c2d42; vertical-align: top;">
                        <strong>Total Invoice Amount in Words :</strong><br><span style="font-style: italic; font-size: 13px;">{amt_words}</span>
                    </td>
                    <td style="width:20%; text-align:right; font-weight:bold; padding: 4px;">Total Amount Before Tax</td><td style="width:15%; text-align:right; padding: 4px; border-left: 1px solid #1c2d42;">{total_before:.2f}</td>
                </tr>
                {tax_rows}
                <tr><td style="text-align:right; font-weight:bold; background-color:#e5e8e8;">Total Amount of Tax</td><td style="text-align:right; font-weight:bold; background-color:#e5e8e8; border-left: 1px solid #1c2d42;">{total_tax:.2f}</td></tr>
                <tr><td style="text-align:right; font-weight:bold; background-color:#d5d8d8; border-bottom: 2px solid #1c2d42;">Total Amount After Tax</td><td style="text-align:right; font-weight:bold; background-color:#d5d8d8; border-left: 1px solid #1c2d42; border-bottom: 2px solid #1c2d42;">{total_after:.2f}</td></tr>
            </table>
            <div class="footer">
                <div style="float: left; width: 60%; font-size: 11px;"><strong>Terms:</strong><br>All disputes are subject to G. B. Nagar Jurisdiction only.</div>
                <div style="float: right; width: 40%; text-align: center;"><span style="font-size: 10px;">Certified that the particulars given are true & correct</span><br><strong>For RAINBOW INDUSTRIES</strong><br><br><br><br><span style="border-top: 1px solid #000; padding-top: 2px;">Authorised Signatory</span></div>
                <div style="clear: both;"></div>
            </div>
        </div>
    </div>
    """

# ==========================================
# 4. APP SYSTEM & SCREENS
# ==========================================
if not st.session_state.get("auth_logged_in"):
    st.title("☁️ SaaS Login")
    u = st.text_input("User ID"); p = st.text_input("Password", type="password")
    if st.button("Login"):
        user = fetch_data("SELECT * FROM users WHERE uid = %s AND password = %s", (u, p))
        if user:
            st.session_state.update({"auth_logged_in": True, "auth_role": user[0]['role'], "auth_name": user[0]['name'], "auth_uid": user[0]['uid']})
            cookie_manager.set("rainbow_erp_auth", "verified"); cookie_manager.set("rainbow_user_role", user[0]['role']); cookie_manager.set("rainbow_user_name", user[0]['name']); cookie_manager.set("rainbow_user_uid", user[0]['uid'])
            time.sleep(0.5); st.rerun()
        else: st.error("❌ Invalid Credentials")
else:
    role = st.session_state.auth_role.upper()
    safe_name = st.session_state.auth_name
    my_company = get_company_profile(st.session_state.auth_uid)
    
    st.sidebar.title("☁️ ERP System")
    st.sidebar.write(f"**Welcome:** {safe_name}")
    if st.sidebar.button("🔒 Logout"):
        for k in ["auth_logged_in", "auth_role", "auth_name", "auth_uid", "form_data", "form_items", "mode", "cust_menu", "redirect_menu", "pdf_comp", "pdf_off", "inv_no"]: st.session_state.pop(k, None)
        cookie_manager.delete("rainbow_erp_auth"); time.sleep(0.5); st.rerun()
    
    if "redirect_menu" in st.session_state:
        st.session_state.cust_menu = st.session_state.redirect_menu
        del st.session_state.redirect_menu

    if role == "SUPERADMIN":
        st.title("👑 Super Admin Dashboard")
        all_users = fetch_data("SELECT * FROM users")
        total_clients = sum(1 for u in all_users if u['role'] == 'customer')
        m1, m2 = st.columns(2); m1.metric("Total Clients", str(total_clients)); m2.metric("Monthly Revenue", f"₹{total_clients * 2499}")
        st.markdown("---")
        with st.form("create_user_form", clear_on_submit=True):
            new_uid = st.text_input("Username / Login ID")
            new_pass = st.text_input("Password", type="password")
            new_fullname = st.text_input("Full Name / Factory Name")
            new_role_select = st.selectbox("Role", ["customer", "superadmin"])
            if st.form_submit_button("🚀 Create Account Live"):
                if execute_data("INSERT INTO users (uid, password, role, name) VALUES (%s, %s, %s, %s)", (new_uid, new_pass, new_role_select, new_fullname)):
                    st.success("Account Created!"); time.sleep(0.5); st.rerun()
        st.subheader("👥 Live User Database")
        st.dataframe(pd.DataFrame(all_users), width="stretch")
    
    elif role == "CUSTOMER":
        menu = st.sidebar.radio("Menu", ["📝 Delivery Challan", "📄 Tax Invoice", "📜 History", "🗑️ Recycle Bin", "⚙️ Company Profile"], key="cust_menu")

        if menu == "⚙️ Company Profile":
            st.title("⚙️ Dynamic Company Profile")
            c_name = st.text_input("Company/Factory Name", value=my_company["name"], key="c_name")
            c_tagline = st.text_input("Tagline (e.g., An ISO 9001:2015 Certified)", value=my_company.get("tagline", ""), key="c_tagline")
            c_gst = st.text_input("GSTIN Number", value=my_company["gstin"], key="c_gst")
            c_address = st.text_area("Registered Address", value=my_company["address"], key="c_address")
            c_state = st.text_input("State", value=my_company["state"], key="c_state")
            c_scode = st.text_input("State Code", value=my_company["state_code"], key="c_scode")
            c_contact = st.text_input("Contact Lines", value=my_company.get("contact", ""), key="c_contact")
            c_manu = st.text_input("Business Scope", value=my_company.get("manufacturing", ""), key="c_manu")
            if st.button("💾 Save Profile", type="primary"):
                execute_data("INSERT INTO company_profiles (uid, name, gstin, address, state, state_code, tagline, contact, manufacturing) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE name=%s, gstin=%s, address=%s, state=%s, state_code=%s, tagline=%s, contact=%s, manufacturing=%s", (st.session_state.auth_uid, c_name, c_gst, c_address, c_state, c_scode, c_tagline, c_contact, c_manu, c_name, c_gst, c_address, c_state, c_scode, c_tagline, c_contact, c_manu))
                st.success("Profile Updated!"); time.sleep(0.5); st.rerun()
            
        elif menu == "📜 History":
            st.title("📜 Document History")
            view_type = st.radio("Select View:", ["Delivery Challans", "Tax Invoices"], horizontal=True)
            
            if view_type == "Delivery Challans":
                data = fetch_data("SELECT id, challan_date, challan_no, party_name, amount FROM challans WHERE created_by = %s AND is_deleted = 0 ORDER BY id DESC LIMIT 50", (safe_name,))
                if data:
                    h1, h2, h3, h4, h5 = st.columns([1.5, 1.5, 3, 2, 2]); h1.write("**Date**"); h2.write("**Challan No**"); h3.write("**Party Name**"); h4.write("**Amount**"); h5.write("**Actions**"); st.markdown("---")
                    for c in data:
                        c1, c2, c3, c4, c5_edit, c5_del = st.columns([1.5, 1.5, 3, 2, 1, 1])
                        c1.write(c['challan_date']); c2.write(c['challan_no']); c3.write(c['party_name']); c4.write(c['amount'])
                        if c5_edit.button("✏️", key=f"ec_{c['id']}"):
                            fd = fetch_data("SELECT * FROM challans WHERE id=%s", (c['id'],))[0]
                            st.session_state.update({"form_data": fd, "form_items": json.loads(fd['items_data']), "mode": "UPDATE", "redirect_menu": "📝 Delivery Challan"}); st.rerun()
                        if c5_del.button("🗑️", key=f"dc_{c['id']}"): execute_data("UPDATE challans SET is_deleted = 1, deleted_at = NOW() WHERE id = %s", (c['id'],)); st.rerun()
                else: st.info("No active Challans found.")
                
            else: # Tax Invoices
                data = fetch_data("SELECT id, invoice_date, invoice_no, bill_to_name, amount FROM tax_invoices WHERE created_by = %s AND is_deleted = 0 ORDER BY id DESC LIMIT 50", (safe_name,))
                if data:
                    h1, h2, h3, h4, h5 = st.columns([1.5, 1.5, 3, 2, 2]); h1.write("**Date**"); h2.write("**Invoice No**"); h3.write("**Party Name**"); h4.write("**Amount**"); h5.write("**Actions**"); st.markdown("---")
                    for c in data:
                        c1, c2, c3, c4, c5_edit, c5_del = st.columns([1.5, 1.5, 3, 2, 1, 1])
                        c1.write(c['invoice_date']); c2.write(c['invoice_no']); c3.write(c['bill_to_name']); c4.write(c['amount'])
                        if c5_edit.button("✏️", key=f"ei_{c['id']}"):
                            fd = fetch_data("SELECT * FROM tax_invoices WHERE id=%s", (c['id'],))[0]
                            st.session_state.update({"form_data": fd, "form_items": json.loads(fd['items_data']), "mode": "UPDATE", "redirect_menu": "📄 Tax Invoice"}); st.rerun()
                        if c5_del.button("🗑️", key=f"di_{c['id']}"): execute_data("UPDATE tax_invoices SET is_deleted = 1, deleted_at = NOW() WHERE id = %s", (c['id'],)); st.rerun()
                else: st.info("No active Tax Invoices found.")

        elif menu == "🗑️ Recycle Bin":
            st.title("🗑️ Recycle Bin")
            view_type = st.radio("Select View:", ["Delivery Challans", "Tax Invoices"], horizontal=True)
            if view_type == "Delivery Challans":
                data = fetch_data("SELECT id, challan_no, party_name, amount FROM challans WHERE created_by = %s AND is_deleted = 1", (safe_name,))
                if data:
                    for c in data:
                        c1, c2, c3, c4 = st.columns([2,3,2,2])
                        c1.write(c['challan_no']); c2.write(c['party_name']); c3.write(c['amount'])
                        if c4.button("🔄 Restore", key=f"rc_{c['id']}"): execute_data("UPDATE challans SET is_deleted = 0, deleted_at = NULL WHERE id = %s", (c['id'],)); st.rerun()
            else:
                data = fetch_data("SELECT id, invoice_no, bill_to_name, amount FROM tax_invoices WHERE created_by = %s AND is_deleted = 1", (safe_name,))
                if data:
                    for c in data:
                        c1, c2, c3, c4 = st.columns([2,3,2,2])
                        c1.write(c['invoice_no']); c2.write(c['bill_to_name']); c3.write(c['amount'])
                        if c4.button("🔄 Restore", key=f"ri_{c['id']}"): execute_data("UPDATE tax_invoices SET is_deleted = 0, deleted_at = NULL WHERE id = %s", (c['id'],)); st.rerun()

        # ==========================================
        # TAX INVOICE ENGINE
        # ==========================================
        elif menu == "📄 Tax Invoice":
            st.title("📄 Tax Invoice Engine")
            
            if st.button("🔄 Clear Form (New Invoice)", key="c_inv"):
                for k in ["form_data", "form_items", "mode", "pdf_comp", "pdf_off", "inv_no"]: st.session_state.pop(k, None)
                st.session_state.item_count = 1; st.rerun()

            fd = st.session_state.get('form_data', {}); fi = st.session_state.get('form_items', []); mode = st.session_state.get('mode', 'INSERT')
            if 'item_count' not in st.session_state: st.session_state.item_count = 1
            if mode == "UPDATE": st.warning("⚠️ EDITING existing Invoice.")

            with st.expander("📌 Invoice & Transport Details", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                invoice_no = c1.text_input("Invoice No.", fd.get('invoice_no',''))
                invoice_date = c2.date_input("Invoice Date", parse_date(fd.get('invoice_date')))
                vendor_code = c3.text_input("Vendor Code", fd.get('vendor_code',''))
                po_no = c4.text_input("P.O. No.", fd.get('po_no',''))
                
                c5, c6, c7, c8 = st.columns(4)
                po_date = c5.date_input("P.O. Date", parse_date(fd.get('po_date')))
                transport_mode = c6.text_input("Transport Mode", fd.get('transport_mode','Road'))
                vehicle_no = c7.text_input("Vehicle No.", fd.get('vehicle_no',''))
                place_of_supply = c8.text_input("Place of Supply", fd.get('place_of_supply',''))
                date_of_supply = st.text_input("Date & Time of Supply", fd.get('date_of_supply',''))

            with st.expander("🏢 Parties Details", expanded=True):
                col_b, col_s = st.columns(2)
                with col_b:
                    st.markdown("**Bill To Party:**")
                    b_name = st.text_input("Name", fd.get('bill_to_name',''), key="b1")
                    b_add = st.text_area("Address", fd.get('bill_to_address',''), key="b2", height=68)
                    b_gst = st.text_input("GSTIN", fd.get('bill_to_gstin',''), key="b3")
                    b_state = st.text_input("State", fd.get('bill_to_state',''), key="b4")
                    b_scode = st.text_input("State Code", fd.get('bill_to_state_code',''), key="b5")
                with col_s:
                    st.markdown("**Shipped To Party:**")
                    same_as = st.checkbox("Same as Bill To")
                    s_name = st.text_input("Name", b_name if same_as else fd.get('ship_to_name',''), key="s1")
                    s_add = st.text_area("Address", b_add if same_as else fd.get('ship_to_address',''), key="s2", height=68)
                    s_gst = st.text_input("GSTIN", b_gst if same_as else fd.get('ship_to_gstin',''), key="s3")
                    s_state = st.text_input("State", b_state if same_as else fd.get('ship_to_state',''), key="s4")
                    s_scode = st.text_input("State Code", b_scode if same_as else fd.get('ship_to_state_code',''), key="s5")

            st.subheader("📦 Item Details")
            col_btn1, col_btn2, _ = st.columns([2, 2, 8])
            if col_btn1.button("➕ Add Item"): st.session_state.item_count += 1; st.rerun()
            if col_btn2.button("➖ Remove Item") and st.session_state.item_count > 1: st.session_state.item_count -= 1; st.rerun()

            items_data = []
            for i in range(st.session_state.item_count):
                ex = fi[i] if i < len(fi) else {}
                c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                with c1: desc = st.text_input(f"Desc {i+1}", ex.get('desc',''), key=f"id_{i}")
                with c2: hsn = st.text_input(f"HSN {i+1}", ex.get('hsn',''), key=f"ih_{i}")
                with c3: boxes = st.text_input(f"Boxes {i+1}", ex.get('boxes',''), key=f"ib_{i}")
                with c4: qty = st.number_input(f"Qty {i+1}", value=float(ex.get('qty',0)), min_value=0.0, key=f"iq_{i}")
                with c5: rate = st.number_input(f"Rate {i+1}", value=float(ex.get('rate',0)), min_value=0.0, key=f"ir_{i}")
                items_data.append({"desc": desc, "hsn": hsn, "boxes": boxes, "qty": qty, "rate": rate, "amount": qty * rate})

            st.markdown("---")
            tax_type = st.radio("Tax Calculation:", ["CGST + SGST (Intra-state)", "IGST (Inter-state)"], horizontal=True)
            tax_mode = "IGST" if "IGST" in tax_type else "CGST"

            if 'pdf_comp' in st.session_state:
                st.success("✅ Invoice Generated & Saved!")
                c_dl1, c_dl2 = st.columns(2)
                c_dl1.download_button("📄 Download Company Copies (3 Pages)", data=st.session_state['pdf_comp'], file_name=f"TaxInvoice_{st.session_state['inv_no']}_Company.pdf", mime="application/pdf", type="primary")
                c_dl2.download_button("📁 Download Office Copy (1 Page)", data=st.session_state['pdf_off'], file_name=f"TaxInvoice_{st.session_state['inv_no']}_OfficeCopy.pdf", mime="application/pdf")
            else:
                if st.button("🚀 Save & Generate Invoice PDF", type="primary"):
                    total_before = sum(item['amount'] for item in items_data)
                    cgst = total_before * 0.09 if tax_mode == "CGST" else 0
                    sgst = total_before * 0.09 if tax_mode == "CGST" else 0
                    igst = total_before * 0.18 if tax_mode == "IGST" else 0
                    total_tax = cgst + sgst + igst
                    total_after = total_before + total_tax
                    amt_words = num2words(total_after, lang='en_IN').title() + " Only."
                    items_json = json.dumps(items_data)

                    if mode == "INSERT": execute_data("""INSERT INTO tax_invoices (created_by, invoice_date, invoice_no, vendor_code, po_no, po_date, bill_to_name, bill_to_address, bill_to_gstin, bill_to_state, bill_to_state_code, ship_to_name, ship_to_address, ship_to_gstin, ship_to_state, ship_to_state_code, transport_mode, vehicle_no, date_of_supply, place_of_supply, items_data, amount, tax_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (safe_name, invoice_date.strftime('%d/%m/%Y'), invoice_no, vendor_code, po_no, po_date.strftime('%d/%m/%Y'), b_name, b_add, b_gst, b_state, b_scode, s_name, s_add, s_gst, s_state, s_scode, transport_mode, vehicle_no, date_of_supply, place_of_supply, items_json, f"₹{total_after:.2f}", tax_mode))
                    else: execute_data("""UPDATE tax_invoices SET invoice_date=%s, invoice_no=%s, vendor_code=%s, po_no=%s, po_date=%s, bill_to_name=%s, bill_to_address=%s, bill_to_gstin=%s, bill_to_state=%s, bill_to_state_code=%s, ship_to_name=%s, ship_to_address=%s, ship_to_gstin=%s, ship_to_state=%s, ship_to_state_code=%s, transport_mode=%s, vehicle_no=%s, date_of_supply=%s, place_of_supply=%s, items_data=%s, amount=%s, tax_type=%s WHERE id=%s""", (invoice_date.strftime('%d/%m/%Y'), invoice_no, vendor_code, po_no, po_date.strftime('%d/%m/%Y'), b_name, b_add, b_gst, b_state, b_scode, s_name, s_add, s_gst, s_state, s_scode, transport_mode, vehicle_no, date_of_supply, place_of_supply, items_json, f"₹{total_after:.2f}", tax_mode, fd['id']))

                    base_css = """<style>@page { size: A4; margin: 10mm; } body { font-family: Arial, sans-serif; font-size: 11px; color: #000; margin:0; padding:0; } .page-break { page-break-after: always; } .page-container { border: 2px solid #1c2d42; width: 100%; box-sizing: border-box; margin-bottom: 20px; position:relative;} .top-label { position: absolute; top: -15px; right: 5px; font-weight: bold; font-size: 10px; background: #fff; padding: 0 5px;} .container { width: 100%; } .header { text-align: center; border-bottom: 2px solid #1c2d42; padding: 10px; position: relative;} .header-left { position: absolute; top: 10px; left: 10px; text-align: left; } .header-right { position: absolute; top: 10px; right: 10px; text-align: right; } table { width: 100%; border-collapse: collapse; } td, th { border: 1px solid #1c2d42; padding: 4px; vertical-align: top; } .info-table td { border-bottom: 2px solid #1c2d42; border-top: none; } .items-table th { border-top: 2px solid #1c2d42; border-bottom: 2px solid #1c2d42; text-align: center; } .spacer-row td { height: 200px; border-bottom: none; border-top:none;} .footer { padding: 5px 10px; border-top: 2px solid #1c2d42; }</style>"""
                    
                    html_1 = generate_tax_invoice_html(my_company, fd, items_data, tax_mode, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, "Original (W)")
                    html_2 = generate_tax_invoice_html(my_company, fd, items_data, tax_mode, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, "Duplicate (P)")
                    html_3 = generate_tax_invoice_html(my_company, fd, items_data, tax_mode, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, "Triplicate (G)")
                    html_4 = generate_tax_invoice_html(my_company, fd, items_data, tax_mode, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, "Office Copy (Y)")

                    full_company_html = f"<!DOCTYPE html><html><head>{base_css}</head><body>{html_1}<div class='page-break'></div>{html_2}<div class='page-break'></div>{html_3}</body></html>"
                    full_office_html = f"<!DOCTYPE html><html><head>{base_css}</head><body>{html_4}</body></html>"
                    
                    st.session_state['pdf_comp'] = HTML(string=full_company_html).write_pdf()
                    st.session_state['pdf_off'] = HTML(string=full_office_html).write_pdf()
                    st.session_state['inv_no'] = invoice_no
                    st.rerun()

        # ==========================================
        # DELIVERY CHALLAN ENGINE (Fully Restored)
        # ==========================================
        elif menu == "📝 Delivery Challan":
            st.title("📝 Delivery Challan Engine")
            
            if st.button("🔄 Clear Form (Make New Challan)", key="c_btn"):
                for key in ["form_data", "form_items", "mode"]:
                    if key in st.session_state: del st.session_state[key]
                st.session_state.item_count = 1; st.rerun()

            fd = st.session_state.get('form_data', {})
            fi = st.session_state.get('form_items', [])
            mode = st.session_state.get('mode', 'INSERT')
            if 'item_count' not in st.session_state: st.session_state.item_count = 1
            if mode == "UPDATE": st.warning("⚠️ EDITING existing challan.")
            
            col1, col2 = st.columns(2)
            with col1:
                party_name = st.text_input("Dispatch To (Party Name)", value=fd.get('party_name', ''), key="p_name")
                party_address = st.text_area("Party Address", value=fd.get('party_address', ''), key="p_add")
                party_gstin = st.text_input("Party GSTIN", value=fd.get('party_gstin', ''), key="p_gst")
                party_state = st.text_input("Party State", value=fd.get('party_state', ''), key="p_state")
                party_state_code = st.text_input("Party State Code", value=fd.get('party_state_code', ''), key="p_scode")
            with col2:
                challan_no = st.text_input("Challan No.", value=fd.get('challan_no', ''), key="c_no")
                vehicle_no = st.text_input("Vehicle No.", value=fd.get('vehicle_no', ''), key="v_no")
                date_of_supply = st.date_input("Date of Supply", parse_date(fd.get('date_of_supply')), key="d_sup")
                challan_date = st.date_input("Challan Date", parse_date(fd.get('challan_date')), key="c_date")
                transport_mode = st.text_input("Transport Mode", value=fd.get('transport_mode', 'Road'), key="t_mode")
                place_of_supply = st.text_input("Place of Supply", value=fd.get('place_of_supply', ''), key="p_sup")

            st.subheader("Item Details")
            c_btn1, c_btn2, _ = st.columns([2, 2, 8])
            if c_btn1.button("➕ Add Item", key="add_item"): st.session_state.item_count += 1; st.rerun()
            if c_btn2.button("➖ Remove Item", key="rem_item") and st.session_state.item_count > 1: st.session_state.item_count -= 1; st.rerun()

            items_data = []
            for i in range(st.session_state.item_count):
                ex = fi[i] if i < len(fi) else {}
                c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                with c1: desc = st.text_input(f"Description {i+1}", ex.get('desc',''), key=f"desc_{i}")
                with c2: hsn = st.text_input(f"HSN {i+1}", ex.get('hsn',''), key=f"hsn_{i}")
                with c3: boxes = st.text_input(f"Boxes {i+1}", ex.get('boxes',''), key=f"box_{i}")
                with c4: qty = st.number_input(f"Qty {i+1}", value=float(ex.get('qty',0)), min_value=0.0, key=f"qty_{i}")
                with c5: rate = st.number_input(f"Rate {i+1}", value=float(ex.get('rate',0)), min_value=0.0, key=f"rate_{i}")
                items_data.append({"desc": desc, "hsn": hsn, "boxes": boxes, "qty": qty, "rate": rate, "amount": qty * rate})

            if st.button("🚀 Save & Print Challan", type="primary", key="save_print_btn"):
                total_before = sum(item['amount'] for item in items_data)
                total_tax = (total_before * 0.09) + (total_before * 0.09)
                total_after = total_before + total_tax
                amt_words = num2words(total_after, lang='en_IN').title() + " Only."
                
                if mode == "INSERT": execute_data("""INSERT INTO challans (created_by, challan_date, challan_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply, transport_mode, place_of_supply, items_data, amount, is_deleted) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)""", (safe_name, challan_date.strftime('%d/%m/%Y'), challan_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply.strftime('%d/%m/%Y'), transport_mode, place_of_supply, json.dumps(items_data), f"₹{total_after:.2f}"))
                else: execute_data("""UPDATE challans SET challan_date=%s, challan_no=%s, party_name=%s, party_address=%s, party_gstin=%s, party_state=%s, party_state_code=%s, vehicle_no=%s, date_of_supply=%s, transport_mode=%s, place_of_supply=%s, items_data=%s, amount=%s WHERE id=%s""", (challan_date.strftime('%d/%m/%Y'), challan_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply.strftime('%d/%m/%Y'), transport_mode, place_of_supply, json.dumps(items_data), f"₹{total_after:.2f}", fd['id']))
                
                items_html = ""
                for idx, item in enumerate(items_data):
                    qty_display = f"{item['qty']} Pcs" if item['qty'] > 0 else ""
                    items_html += f"<tr><td style='text-align:center;'>{idx+1}.</td><td><strong>{item['desc'].replace(chr(10), '<br>')}</strong></td><td style='text-align:center;'>{item['hsn']}</td><td style='text-align:center;'>{item['boxes']}</td><td style='text-align:center;'>{qty_display}</td><td style='text-align:right;'>{item['rate']:.2f}</td><td style='text-align:right;'>{item['amount']:.2f}</td></tr>"

                html_content = f"""
                <!DOCTYPE html><html><head><style>@page {{ size: A4; margin: 15mm; }} body {{ font-family: Arial, sans-serif; font-size: 12px; color: #1c2d42; }} .container {{ border: 2px solid #1c2d42; width: 100%; }} .header {{ text-align: center; border-bottom: 2px solid #1c2d42; padding: 15px 10px; background-color: #fcfcfc; position: relative; min-height: 110px; }} .header h2 {{ margin: 0 0 5px 0; font-size: 18px; text-decoration: underline; letter-spacing: 1.5px; font-weight: bold; }} .header h1 {{ margin: 5px 0; font-size: 32px; font-weight: 900; }} .top-left-info {{ position: absolute; top: 15px; left: 15px; text-align: left; font-size: 12px; }} table {{ width: 100%; border-collapse: collapse; }} td, th {{ border: 1px solid #aeb6bf; padding: 6px; vertical-align: top; }} .items-table th {{ background-color: #e5e8e8; text-align: center; border-bottom: 2px solid #1c2d42; border-top: 2px solid #1c2d42; }} .spacer-row td {{ height: 150px; border-top: none; border-bottom: none; }} .footer {{ padding: 10px; height: 100px; border-top: 2px solid #1c2d42; position: relative; }} .signature {{ position: absolute; right: 20px; bottom: 10px; text-align: center; width: 200px; }}</style></head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="top-left-info"><strong>GSTIN:</strong> {my_company['gstin']}<br><strong>State:</strong> {my_company['state']}<br><strong>Code:</strong> {my_company['state_code']}</div>
                            <h2>DELIVERY CHALLAN</h2><h1>{my_company['name']}</h1><p>{my_company['tagline']}</p><p>{my_company['address']}</p><p>{my_company['contact']}</p><p style="font-weight: bold; font-size: 13px; margin-top: 5px;">{my_company['manufacturing']}</p>
                        </div>
                        <table>
                            <tr>
                                <td style="width: 50%; border-right: 2px solid #1c2d42;"><strong>Dispatch To:</strong><br><strong>{party_name}</strong><br>{party_address.replace(chr(10), '<br>')}<br><strong>GSTIN:</strong> {party_gstin}<br><strong>State:</strong> {party_state} &nbsp;&nbsp;&nbsp; <strong>Code:</strong> {party_state_code}</td>
                                <td style="width: 50%; padding: 0;">
                                    <table style="border:none; width: 100%;">
                                        <tr><td style="border:none; width: 50%; padding-bottom: 4px;"><strong>Challan No:</strong> {challan_no}</td><td style="border:none; border-left: 1px solid #aeb6bf; width: 50%; padding-bottom: 4px;"><strong>Date:</strong> {challan_date.strftime('%d/%m/%Y')}</td></tr>
                                        <tr><td style="border:none; border-top: 1px solid #aeb6bf; padding-top: 4px; padding-bottom: 4px;"><strong>Vehicle:</strong> {vehicle_no}</td><td style="border:none; border-top: 1px solid #aeb6bf; border-left: 1px solid #aeb6bf; padding-top: 4px; padding-bottom: 4px;"><strong>Transport Mode:</strong> {transport_mode}</td></tr>
                                        <tr><td style="border:none; border-top: 1px solid #aeb6bf; padding-top: 4px;"><strong>Date of Supply:</strong> {date_of_supply.strftime('%d/%m/%Y')}</td><td style="border:none; border-top: 1px solid #aeb6bf; border-left: 1px solid #aeb6bf; padding-top: 4px;"><strong>Place of Supply:</strong> {place_of_supply}</td></tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                        <table class="items-table">
                            <tr><th style="width:5%;">S.No</th><th style="width:35%;">Product Description</th><th style="width:10%;">HSN Code</th><th style="width:10%;">No of Box</th><th style="width:10%;">Total Qty</th><th style="width:12%;">Approx. Rate</th><th style="width:18%;">Approx. Amount</th></tr>
                            {items_html}<tr class="spacer-row"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
                        </table>
                        <table style="border-top: 2px solid #1c2d42;">
                            <tr><td rowspan="5" style="width:60%; padding-left:10px;"><strong>Total Amount in Words:</strong><br><em>{amt_words}</em></td><td style="width:20%; text-align:right; background-color:#f8f9fa;">Total Before Tax</td><td style="width:20%; text-align:right;">{total_before:.2f}</td></tr>
                            <tr><td style="text-align:right; background-color:#f8f9fa;">Add: CGST @ 9%</td><td style="text-align:right;">{total_before * 0.09:.2f}</td></tr>
                            <tr><td style="text-align:right; background-color:#f8f9fa;">Add: SGST @ 9%</td><td style="text-align:right;">{total_before * 0.09:.2f}</td></tr>
                            <tr><td style="text-align:right; background-color:#f8f9fa; font-weight:bold;">Total Amount of Tax</td><td style="text-align:right; font-weight:bold;">{total_tax:.2f}</td></tr>
                            <tr><td style="text-align:right; font-weight:bold; background-color:#e5e8e8;">Total After Tax</td><td style="text-align:right; font-weight:bold; background-color:#e5e8e8;">{total_after:.2f}</td></tr>
                        </table>
                        <div class="footer"><p style="font-size: 10px;">Certified That The Particulars given Above are true and correct.</p><div class="signature"><p>For <strong>{my_company['name'].upper()}</strong></p><br><br><p style="border-top:1px solid #000; font-size:10px;">Authorised Signature</p></div></div>
                    </div>
                </body></html>"""
                
                pdf_c = HTML(string=html_content).write_pdf()
                st.download_button(label="📄 Download Ready PDF", data=pdf_c, file_name=f"Challan_{challan_no if challan_no else 'New'}.pdf", mime="application/pdf")