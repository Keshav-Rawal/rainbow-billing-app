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
import re
import tempfile
import os

# 3D Libraries Load Check
try:
    import trimesh
    import plotly.graph_objects as go
    HAS_3D = True
except ImportError:
    HAS_3D = False

# AI Library Load Check
try:
    import google.generativeai as genai
    HAS_AI = True
except ImportError:
    HAS_AI = False

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
            cursor.execute("CREATE TABLE IF NOT EXISTS challans (id INT AUTO_INCREMENT PRIMARY KEY, created_by VARCHAR(100), challan_date VARCHAR(20), challan_no VARCHAR(50), eway_bill_no VARCHAR(50), party_name VARCHAR(100), party_address TEXT, party_gstin VARCHAR(50), party_state VARCHAR(50), party_state_code VARCHAR(20), vehicle_no VARCHAR(50), date_of_supply VARCHAR(50), transport_mode VARCHAR(50), place_of_supply VARCHAR(100), items_data TEXT, amount VARCHAR(50), is_deleted INT DEFAULT 0, deleted_at DATETIME NULL)")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tax_invoices (
                    id INT AUTO_INCREMENT PRIMARY KEY, created_by VARCHAR(100), invoice_date VARCHAR(20), invoice_no VARCHAR(50), eway_bill_no VARCHAR(50), vendor_code VARCHAR(50), po_no VARCHAR(50), po_date VARCHAR(20), bill_to_name VARCHAR(100), bill_to_address TEXT, bill_to_gstin VARCHAR(50), bill_to_state VARCHAR(50), bill_to_state_code VARCHAR(20), ship_to_name VARCHAR(100), ship_to_address TEXT, ship_to_gstin VARCHAR(50), ship_to_state VARCHAR(50), ship_to_state_code VARCHAR(20), transport_mode VARCHAR(50), vehicle_no VARCHAR(50), date_of_supply VARCHAR(50), place_of_supply VARCHAR(100), items_data TEXT, amount VARCHAR(50), tax_type VARCHAR(20), is_deleted INT DEFAULT 0, deleted_at DATETIME NULL
                )
            """)
            
            cursor.execute("CREATE TABLE IF NOT EXISTS party_master (id INT AUTO_INCREMENT PRIMARY KEY, uid VARCHAR(50), party_name VARCHAR(255), address TEXT, gstin VARCHAR(20), state VARCHAR(100), state_code VARCHAR(10), place_of_supply VARCHAR(100))")
            cursor.execute("CREATE TABLE IF NOT EXISTS item_master (id INT AUTO_INCREMENT PRIMARY KEY, uid VARCHAR(50), party_name VARCHAR(255), item_description VARCHAR(255), hsn_code VARCHAR(20), rate FLOAT DEFAULT 0.0)")

            try: cursor.execute("ALTER TABLE item_master ADD COLUMN party_name VARCHAR(255)"); conn.commit()
            except: pass
            try: cursor.execute("ALTER TABLE party_master ADD COLUMN place_of_supply VARCHAR(100)"); conn.commit()
            except: pass
            try: cursor.execute("ALTER TABLE item_master ADD COLUMN rate FLOAT DEFAULT 0.0"); conn.commit()
            except: pass
            try: cursor.execute("ALTER TABLE tax_invoices ADD COLUMN eway_bill_no VARCHAR(50)"); conn.commit()
            except: pass
            try: cursor.execute("ALTER TABLE challans ADD COLUMN eway_bill_no VARCHAR(50)"); conn.commit()
            except: pass

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
    return data[0] if data else {"name": "RAINBOW INDUSTRIES", "gstin": "09AAAAA0000A1Z1", "address": "2804, Dhoom Manikpur, Dadri (G.B. Nagar) U.P. 203207", "state": "UP", "state_code": "09", "tagline": "(An ISO 9001:2015 Certified Company)", "contact": "Mob.: 9711325563, 8826366314 | Email: rainbowindustries647@gmail.com", "manufacturing": "Manufactures of : Plastic Components, Automobiles, Electricals & Electronics"}

def parse_date(date_str):
    if date_str:
        try: return datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
        except: pass
    return datetime.date.today()

def get_next_auto_no(table_name, col_name, created_by):
    data = fetch_data(f"SELECT {col_name} FROM {table_name} WHERE created_by = %s ORDER BY id DESC LIMIT 1", (created_by,))
    if data and data[0][col_name]:
        val = str(data[0][col_name])
        m = re.search(r'(\d+)$', val)
        if m:
            num_str = m.group(1)
            padded_num = str(int(num_str) + 1).zfill(len(num_str))
            return val[:-len(num_str)] + padded_num
        return val + "-1"
    return "1"

def get_ist_time():
    ist_time = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    return ist_time.strftime("%d/%m/%Y %I:%M %p")

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

if "cust_menu" not in st.session_state: st.session_state.cust_menu = "🏢 Dashboard"

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
        
    eway_html = f"<tr><td style='border:none; padding:4px;'><strong>E-Way Bill No.</strong></td><td style='border:none; padding:4px;'>: <strong>{fd.get('eway_bill_no','')}</strong></td></tr>" if fd.get('eway_bill_no') else ""

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
                            {eway_html}
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
    if not st.session_state.get('auth_role'):
        st.session_state['auth_logged_in'] = False
        st.rerun()

    role = st.session_state.auth_role.upper()
    safe_name = st.session_state.auth_name
    uid = st.session_state.auth_uid
    my_company = get_company_profile(uid)
    
    st.sidebar.title("☁️ ERP System")
    st.sidebar.write(f"**Welcome:** {safe_name}")
    if st.sidebar.button("🔒 Logout"):
        for k in list(st.session_state.keys()):
            if k not in ["cookie_manager"]: st.session_state.pop(k, None)
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
        # YAHAN MENU MEIN AI ASSISTANT ADD KIYA HAI
        menu = st.sidebar.radio("Menu", ["🏢 Dashboard", "📝 Delivery Challan", "📄 Tax Invoice", "📐 3D Part Viewer", "📦 Add Master Data", "📜 History", "🗑️ Recycle Bin", "⚙️ Company Profile", "🤖 AI Assistant"], key="cust_menu")

        if menu == "🏢 Dashboard":
            st.title("🏢 Client Dashboard")
            st.write("Aapke saare permanent vendors aur clients yahan hain. Ek click mein unka specific Bill ya Challan banayein!")
            st.markdown("---")
            
            parties_db = fetch_data("SELECT * FROM party_master WHERE uid=%s", (uid,))
            
            if not parties_db:
                st.info("Abhi tak koi Client add nahi kiya hai. Left menu se '📦 Add Master Data' mein jaakar apni pehli party add karein.")
            else:
                cols = st.columns(3)
                for idx, p in enumerate(parties_db):
                    with cols[idx % 3]:
                        st.markdown(f"#### 🏢 {p['party_name']}")
                        st.caption(f"**State:** {p['state']} | **GST:** {p['gstin']}")
                        
                        c_inv, c_chal = st.columns(2)
                        if c_inv.button("📄 Invoice", key=f"d_inv_{p['id']}", use_container_width=True):
                            st.session_state['sel_inv_p'] = p['party_name']
                            st.session_state.redirect_menu = "📄 Tax Invoice"
                            st.rerun()
                            
                        if c_chal.button("📝 Challan", key=f"d_chal_{p['id']}", use_container_width=True):
                            st.session_state['sel_chal_p'] = p['party_name']
                            st.session_state.redirect_menu = "📝 Delivery Challan"
                            st.rerun()
                            
                        if st.button("🗑️ Delete Party", key=f"d_del_{p['id']}", use_container_width=True):
                            execute_data("DELETE FROM party_master WHERE id=%s", (p['id'],))
                            execute_data("DELETE FROM item_master WHERE party_name=%s AND uid=%s", (p['party_name'], uid)) 
                            st.rerun()
                        
                        st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

        elif menu == "⚙️ Company Profile":
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
                execute_data("INSERT INTO company_profiles (uid, name, gstin, address, state, state_code, tagline, contact, manufacturing) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE name=%s, gstin=%s, address=%s, state=%s, state_code=%s, tagline=%s, contact=%s, manufacturing=%s", (uid, c_name, c_gst, c_address, c_state, c_scode, c_tagline, c_contact, c_manu, c_name, c_gst, c_address, c_state, c_scode, c_tagline, c_contact, c_manu))
                st.success("Profile Updated!"); time.sleep(0.5); st.rerun()
            
        elif menu == "📦 Add Master Data":
            st.title("📦 Master Data Management")
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("👥 Add New Party")
                with st.form("p_m", clear_on_submit=True):
                    pn = st.text_input("Party Name *")
                    pa = st.text_area("Address *")
                    pg = st.text_input("GSTIN")
                    ps = st.text_input("State")
                    pc = st.text_input("State Code")
                    ppos = st.text_input("Place of Supply (City/State)")
                    if st.form_submit_button("Save Party"):
                        if pn and pa:
                            execute_data("INSERT INTO party_master (uid, party_name, address, gstin, state, state_code, place_of_supply) VALUES (%s, %s, %s, %s, %s, %s, %s)", (uid, pn, pa, pg, ps, pc, ppos))
                            st.success(f"Party '{pn}' Saved Successfully!")
                        else: st.error("Name and Address are required!")

            with c2:
                st.subheader("📦 Add Items specific to a Party")
                saved_parties = [p['party_name'] for p in fetch_data("SELECT party_name FROM party_master WHERE uid=%s", (uid,))]
                
                if not saved_parties:
                    st.warning("⚠️ Pehle left side se Party add karein, fir uske items add kar payenge.")
                else:
                    with st.form("i_m", clear_on_submit=True):
                        linked_party = st.selectbox("Select Party for this Item *", saved_parties)
                        idsc = st.text_input("Item Description *")
                        ihsn = st.text_input("HSN Code")
                        irate = st.number_input("Default Rate (₹)", min_value=0.0, step=1.0)
                        
                        if st.form_submit_button("Save Item for this Party"):
                            if idsc:
                                execute_data("INSERT INTO item_master (uid, party_name, item_description, hsn_code, rate) VALUES (%s, %s, %s, %s, %s)", (uid, linked_party, idsc, ihsn, irate))
                                st.success(f"Item saved specifically for {linked_party}!")
                            else: st.error("Item Description is required!")
                
                saved_items = fetch_data("SELECT id, party_name, item_description, hsn_code, rate FROM item_master WHERE uid=%s", (uid,))
                if saved_items:
                    with st.expander("🗑️ View / Delete Saved Items"):
                        for itm in saved_items:
                            col_a, col_b = st.columns([4, 1])
                            col_a.write(f"**{itm['party_name']}** ➔ {itm['item_description']} (HSN: {itm['hsn_code']} | Rate: ₹{itm.get('rate', 0.0)})")
                            if col_b.button("Del", key=f"del_it_{itm['id']}"):
                                execute_data("DELETE FROM item_master WHERE id=%s", (itm['id'],))
                                st.rerun()

        # ==========================================
        # 3D DRAWING VIEWER & MEASUREMENT MODULE
        # ==========================================
        elif menu == "📐 3D Part Viewer":
            st.title("📐 Pro 3D CAD Viewer & Weight Calculator")
            st.write("Ab **.STL aur .OBJ** files upload karein. Exact theoretical weight ke sath apna Factory Margin bhi lagayein!")
            
            if not HAS_3D:
                st.error("⚠️ 3D Libraries missing! Backend me `pip install trimesh plotly scipy networkx` install hona chahiye.")
            else:
                MATERIALS = {
                    "PP Plastic (Polypropylene)": 0.90,
                    "ABS Plastic": 1.04,
                    "Aluminium": 2.70,
                    "SS304 (Stainless Steel)": 7.93,
                    "Copper": 8.96,
                    "Nylon": 1.15,
                }

                col_mat, col_slider = st.columns([1, 1])
                with col_mat:
                    selected_material = st.selectbox("Select Material for Calculation", list(MATERIALS.keys()))
                with col_slider:
                    margin_pct = st.slider("⚙️ Factory Machining / Scrap Margin (%)", min_value=0.0, max_value=25.0, value=0.0, step=0.5, help="Actual factory weight nikalne ke liye machining tolerance ya scrap waste ka margin add karein.")

                uploaded_file = st.file_uploader("Upload a 3D File (.stl, .obj)", type=['stl', 'obj'])
                
                if uploaded_file is not None:
                    file_extension = uploaded_file.name.split('.')[-1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix="." + file_extension) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    try:
                        with st.spinner("Analyzing 3D Mesh... Please wait"):
                            mesh = trimesh.load(tmp_path)
                            
                            vol_mm3 = mesh.volume
                            area_mm2 = mesh.area
                            bbox = mesh.bounding_box.extents
                            
                            vol_cm3 = vol_mm3 * 0.001
                            density = MATERIALS[selected_material]
                            
                            theoretical_weight = vol_cm3 * density
                            practical_weight = theoretical_weight * (1 + (margin_pct / 100))
                            
                            st.success(f"✅ Part Loaded Successfully: {uploaded_file.name}")
                            
                            st.subheader("📊 Part Details & Weights")
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Dimensions (L x W x H)", f"{bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f} mm")
                            m2.metric("Surface Area", f"{area_mm2:,.0f} mm²")
                            m3.metric("Theoretical Weight", f"{theoretical_weight:,.2f} g")
                            
                            m4.metric(f"🛠️ Practical Weight (+{margin_pct}%)", f"{practical_weight:,.2f} g", delta_color="normal")
                            
                            st.markdown("---")
                            st.subheader("🔍 Interactive 3D View")
                            
                            vertices = mesh.vertices
                            faces = mesh.faces
                            
                            mesh_color = 'silver' if "Aluminium" in selected_material or "SS304" in selected_material else '#1a4f8b'

                            fig = go.Figure(data=[
                                go.Mesh3d(
                                    x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
                                    i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
                                    color=mesh_color, opacity=0.85,
                                    lighting=dict(ambient=0.5, diffuse=1, roughness=0.5, specular=0.5)
                                )
                            ])
                            
                            fig.update_layout(
                                scene=dict(
                                    aspectmode='data',
                                    xaxis=dict(visible=False),
                                    yaxis=dict(visible=False),
                                    zaxis=dict(visible=False)
                                ),
                                margin=dict(l=0, r=0, b=0, t=0),
                                height=550
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                    except Exception as e:
                        st.error(f"Error loading 3D File: {e}. Kripya ensure karein ki aapne sahi STL/OBJ file daali hai.")
                    finally:
                        os.remove(tmp_path)

        # ==========================================
        # AI ASSISTANT MODULE (NEW PHASE 3)
        # ==========================================
        elif menu == "🤖 AI Assistant":
            st.title("🤖 Rainbow AI Assistant")
            st.write("Aapke ERP ka smart helper! Puchiye app kaise use karna hai, kaise bill banana hai, ya koi bhi dusra sawal.")
            st.markdown("---")

            if not HAS_AI:
                st.error("⚠️ AI Library missing! Backend me `pip install google-generativeai` install karein.")
            else:
                # API Key Input
                if "gemini_api_key" not in st.session_state:
                    st.session_state.gemini_api_key = ""
                
                if not st.session_state.gemini_api_key:
                    st.info("💡 AI chalane ke liye ek free Google Gemini API key ki zaroorat hai. (Google AI Studio se mil jayegi)")
                    api_input = st.text_input("Enter Gemini API Key:", type="password")
                    if st.button("Save Key & Start AI"):
                        st.session_state.gemini_api_key = api_input
                        st.rerun()
                else:
                    try:
                        genai.configure(api_key=st.session_state.gemini_api_key)
                        
                        # THE SECRET SYSTEM PROMPT (Brain of our AI)
                        sys_prompt = """Tumhara naam 'Rainbow AI' hai. Tum Rainbow ERP ke ek smart aur helpful assistant ho. 
                        Tumhara kaam staff ko ERP use karna sikhana hai. 
                        ERP me yeh 5 main features hain:
                        1. Dashboard: Yahan se direct kisi bhi party ka bill/challan bana sakte hain.
                        2. Add Master Data: Yahan naye client ka naam, GST aur uske specific items save hote hain.
                        3. Tax Invoice & Delivery Challan: Master data se autofill karke bill banate hain. IGST/CGST automatically calculate hota hai.
                        4. 3D Part Viewer: Factory waale .STL file upload karke plastic part (PP, ABS) ka exact weight aur factory margin nikal sakte hain.
                        5. History: Purane bills dekhne ke liye.
                        
                        Tumhe humesha friendly, professional aur 'Hinglish' (Hindi + English) bhasha mein chote aur clear points mein jawab dena hai. Jawab mein zaroorat padne par emojis ka use karein. Kabhi bhi code ya programming ki baatein na karein, sirf user/staff ki madad karein."""

                        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=sys_prompt)

                        # Chat History setup
                        if "chat_history" not in st.session_state:
                            st.session_state.chat_history = []
                            # Initial greeting
                            st.session_state.chat_history.append({"role": "model", "parts": ["Namaste! Main Rainbow AI hoon. Batayiye, aaj main ERP mein aapki kya madad kar sakta hoon?"]})

                        # Show previous chat messages
                        for msg in st.session_state.chat_history:
                            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                                st.markdown(msg["parts"][0])

                        # Chat input field
                        prompt = st.chat_input("Puchiye, jaise 'Naya Invoice kaise banau?'")
                        
                        if prompt:
                            # Save user message
                            st.session_state.chat_history.append({"role": "user", "parts": [prompt]})
                            with st.chat_message("user"):
                                st.markdown(prompt)
                                
                            # Get AI response
                            with st.chat_message("assistant"):
                                with st.spinner("AI Soch raha hai..."):
                                    # Passing previous conversation history so it remembers context
                                    chat = model.start_chat(history=st.session_state.chat_history[:-1])
                                    response = chat.send_message(prompt)
                                    st.markdown(response.text)
                                    # Save AI response
                                    st.session_state.chat_history.append({"role": "model", "parts": [response.text]})
                                    
                        if st.button("🗑️ Clear Chat History"):
                            st.session_state.chat_history = []
                            st.rerun()

                    except Exception as e:
                        st.error("❌ API Key shayad galat hai ya internet issue hai. Check karke dobara try karein.")
                        if st.button("Change API Key"):
                            st.session_state.gemini_api_key = ""
                            st.rerun()

        elif menu == "📜 History":
            st.title("📜 Document History & Analytics")
            view_type = st.radio("Select View:", ["Delivery Challans", "Tax Invoices"], horizontal=True)
            
            if view_type == "Delivery Challans":
                party_list = fetch_data("SELECT DISTINCT party_name FROM challans WHERE created_by = %s AND is_deleted = 0", (safe_name,))
                p_names = ["All Parties"] + [p['party_name'] for p in party_list]
                sel_history_p = st.selectbox("🔍 Filter by Party Name", p_names, key="hist_chal")

                if sel_history_p == "All Parties":
                    data = fetch_data("SELECT id, challan_date, challan_no, party_name, amount FROM challans WHERE created_by = %s AND is_deleted = 0 ORDER BY id DESC", (safe_name,))
                else:
                    data = fetch_data("SELECT id, challan_date, challan_no, party_name, amount FROM challans WHERE created_by = %s AND party_name = %s AND is_deleted = 0 ORDER BY id DESC", (safe_name, sel_history_p))
                
                if data:
                    df = pd.DataFrame(data)
                    df['clean_amt'] = df['amount'].apply(lambda x: float(str(x).replace('₹','').replace(',','').strip()) if x else 0.0)
                    df['date_obj'] = pd.to_datetime(df['challan_date'], format='%d/%m/%Y', errors='coerce')
                    
                    st.markdown(f"### 📈 {sel_history_p} Analytics")
                    c1, c2 = st.columns(2)
                    c1.metric("🧾 Total Challans Issued", f"{len(df)}")
                    c2.metric("💰 Total Value of Challans", f"₹ {df['clean_amt'].sum():,.2f}")
                    
                    valid_dates = df.dropna(subset=['date_obj']).copy()
                    if not valid_dates.empty:
                        valid_dates['month_str'] = valid_dates['date_obj'].dt.strftime('%b %Y')
                        valid_dates['sort_key'] = valid_dates['date_obj'].dt.strftime('%Y-%m')
                        grouped = valid_dates.groupby(['sort_key', 'month_str'])['clean_amt'].sum().reset_index().sort_values('sort_key')
                        chart_data = grouped.set_index('month_str')['clean_amt']
                        st.bar_chart(chart_data)
                    
                    st.markdown("---")
                    st.write("**Recent Challan Records:**")

                    h1, h2, h3, h4, h5 = st.columns([1.5, 1.5, 3, 2, 2]); h1.write("**Date**"); h2.write("**Challan No**"); h3.write("**Party Name**"); h4.write("**Amount**"); h5.write("**Actions**")
                    for c in data[:50]:
                        c1, c2, c3, c4, c5_edit, c5_del = st.columns([1.5, 1.5, 3, 2, 1, 1])
                        c1.write(c['challan_date']); c2.write(c['challan_no']); c3.write(c['party_name']); c4.write(c['amount'])
                        if c5_edit.button("✏️", key=f"ec_{c['id']}"):
                            fd = fetch_data("SELECT * FROM challans WHERE id=%s", (c['id'],))[0]
                            st.session_state.update({"form_data": fd, "form_items": json.loads(fd['items_data']), "mode": "UPDATE", "redirect_menu": "📝 Delivery Challan"}); st.rerun()
                        if c5_del.button("🗑️", key=f"dc_{c['id']}"): execute_data("UPDATE challans SET is_deleted = 1, deleted_at = NOW() WHERE id = %s", (c['id'],)); st.rerun()
                else: st.info("No active Challans found for this selection.")
            else:
                party_list = fetch_data("SELECT DISTINCT bill_to_name FROM tax_invoices WHERE created_by = %s AND is_deleted = 0", (safe_name,))
                p_names = ["All Parties"] + [p['bill_to_name'] for p in party_list]
                sel_history_p = st.selectbox("🔍 Filter by Party Name", p_names, key="hist_inv")

                if sel_history_p == "All Parties":
                    data = fetch_data("SELECT id, invoice_date, invoice_no, bill_to_name, amount FROM tax_invoices WHERE created_by = %s AND is_deleted = 0 ORDER BY id DESC", (safe_name,))
                else:
                    data = fetch_data("SELECT id, invoice_date, invoice_no, bill_to_name, amount FROM tax_invoices WHERE created_by = %s AND bill_to_name = %s AND is_deleted = 0 ORDER BY id DESC", (safe_name, sel_history_p))
                
                if data:
                    df = pd.DataFrame(data)
                    df['clean_amt'] = df['amount'].apply(lambda x: float(str(x).replace('₹','').replace(',','').strip()) if x else 0.0)
                    df['date_obj'] = pd.to_datetime(df['invoice_date'], format='%d/%m/%Y', errors='coerce')
                    
                    st.markdown(f"### 📈 {sel_history_p} Analytics")
                    c1, c2 = st.columns(2)
                    c1.metric("🧾 Total Tax Invoices", f"{len(df)}")
                    c2.metric("💰 Total Billing Amount", f"₹ {df['clean_amt'].sum():,.2f}")
                    
                    valid_dates = df.dropna(subset=['date_obj']).copy()
                    if not valid_dates.empty:
                        valid_dates['month_str'] = valid_dates['date_obj'].dt.strftime('%b %Y')
                        valid_dates['sort_key'] = valid_dates['date_obj'].dt.strftime('%Y-%m')
                        grouped = valid_dates.groupby(['sort_key', 'month_str'])['clean_amt'].sum().reset_index().sort_values('sort_key')
                        chart_data = grouped.set_index('month_str')['clean_amt']
                        st.bar_chart(chart_data)
                        
                    st.markdown("---")
                    st.write("**Recent Invoice Records:**")

                    h1, h2, h3, h4, h5 = st.columns([1.5, 1.5, 3, 2, 2]); h1.write("**Date**"); h2.write("**Invoice No**"); h3.write("**Party Name**"); h4.write("**Amount**"); h5.write("**Actions**")
                    for c in data[:50]:
                        c1, c2, c3, c4, c5_edit, c5_del = st.columns([1.5, 1.5, 3, 2, 1, 1])
                        c1.write(c['invoice_date']); c2.write(c['invoice_no']); c3.write(c['bill_to_name']); c4.write(c['amount'])
                        if c5_edit.button("✏️", key=f"ei_{c['id']}"):
                            fd = fetch_data("SELECT * FROM tax_invoices WHERE id=%s", (c['id'],))[0]
                            st.session_state.update({"form_data": fd, "form_items": json.loads(fd['items_data']), "mode": "UPDATE", "redirect_menu": "📄 Tax Invoice"}); st.rerun()
                        if c5_del.button("🗑️", key=f"di_{c['id']}"): execute_data("UPDATE tax_invoices SET is_deleted = 1, deleted_at = NOW() WHERE id = %s", (c['id'],)); st.rerun()
                else: st.info("No active Tax Invoices found for this selection.")

        elif menu == "🗑️ Recycle Bin":
            st.title("🗑️ Recycle Bin")
            view_type = st.radio("Select View:", ["Delivery Challans", "Tax Invoices"], horizontal=True)
            
            if view_type == "Delivery Challans":
                data = fetch_data("SELECT id, challan_no, party_name, amount FROM challans WHERE created_by = %s AND is_deleted = 1", (safe_name,))
                if data:
                    if st.button("🚨 Empty Entire Challan Bin", type="primary"):
                        execute_data("DELETE FROM challans WHERE created_by = %s AND is_deleted = 1", (safe_name,))
                        st.rerun()
                    st.markdown("---")
                    for c in data:
                        c1, c2, c3, c4, c5 = st.columns([2,3,2,1.5,1.5])
                        c1.write(c['challan_no']); c2.write(c['party_name']); c3.write(c['amount'])
                        if c4.button("🔄 Restore", key=f"rc_{c['id']}"): execute_data("UPDATE challans SET is_deleted = 0, deleted_at = NULL WHERE id = %s", (c['id'],)); st.rerun()
                        if c5.button("❌ Delete", key=f"dc_perm_{c['id']}"): execute_data("DELETE FROM challans WHERE id = %s", (c['id'],)); st.rerun()
                else: st.info("Challan Recycle Bin is clean! ✨")
            else:
                data = fetch_data("SELECT id, invoice_no, bill_to_name, amount FROM tax_invoices WHERE created_by = %s AND is_deleted = 1", (safe_name,))
                if data:
                    if st.button("🚨 Empty Entire Invoice Bin", type="primary"):
                        execute_data("DELETE FROM tax_invoices WHERE created_by = %s AND is_deleted = 1", (safe_name,))
                        st.rerun()
                    st.markdown("---")
                    for c in data:
                        c1, c2, c3, c4, c5 = st.columns([2,3,2,1.5,1.5])
                        c1.write(c['invoice_no']); c2.write(c['bill_to_name']); c3.write(c['amount'])
                        if c4.button("🔄 Restore", key=f"ri_{c['id']}"): execute_data("UPDATE tax_invoices SET is_deleted = 0, deleted_at = NULL WHERE id = %s", (c['id'],)); st.rerun()
                        if c5.button("❌ Delete", key=f"di_perm_{c['id']}"): execute_data("DELETE FROM tax_invoices WHERE id = %s", (c['id'],)); st.rerun()
                else: st.info("Tax Invoice Recycle Bin is clean! ✨")

        # ==========================================
        # TAX INVOICE ENGINE
        # ==========================================
        elif menu == "📄 Tax Invoice":
            st.title("📄 Tax Invoice Engine")
            parties_db = fetch_data("SELECT * FROM party_master WHERE uid=%s", (uid,))
            
            if st.button("🔄 Clear Form (New Invoice)", key="c_inv"):
                preserve = ["auth_logged_in", "auth_role", "auth_name", "auth_uid", "cookie_manager", "cust_menu", "db_initialized"]
                for k in list(st.session_state.keys()):
                    if k not in preserve: st.session_state.pop(k, None)
                st.session_state.item_count = 1; st.rerun()

            fd = st.session_state.get('form_data', {}); fi = st.session_state.get('form_items', []); mode = st.session_state.get('mode', 'INSERT')
            if 'item_count' not in st.session_state: st.session_state.item_count = 1
            if mode == "UPDATE": st.warning("⚠️ EDITING existing Invoice.")

            def_inv_no = fd.get('invoice_no', get_next_auto_no('tax_invoices', 'invoice_no', safe_name)) if mode == "INSERT" else fd.get('invoice_no','')
            def_date_time = get_ist_time()

            dash_party = st.session_state.pop('sel_inv_p', None)
            party_names = ["-- Select Party from Master --"] + [p['party_name'] for p in parties_db]
            default_idx = party_names.index(dash_party) if dash_party in party_names else 0

            if dash_party and dash_party != "-- Select Party from Master --":
                pm = next((p for p in parties_db if p['party_name'] == dash_party), None)
                if pm:
                    st.session_state.b1 = pm['party_name']
                    st.session_state.b2 = pm['address']
                    st.session_state.b3 = pm['gstin']
                    st.session_state.b4 = pm['state']
                    st.session_state.b5 = pm['state_code']
                    st.session_state.pos_inv = pm.get('place_of_supply', '')
            elif 'b1' not in st.session_state:
                st.session_state.b1 = fd.get('bill_to_name', '')
                st.session_state.b2 = fd.get('bill_to_address', '')
                st.session_state.b3 = fd.get('bill_to_gstin', '')
                st.session_state.b4 = fd.get('bill_to_state', '')
                st.session_state.b5 = fd.get('bill_to_state_code', '')
                st.session_state.pos_inv = fd.get('place_of_supply', '')

            with st.expander("📌 Invoice & Transport Details", expanded=True):
                c1, c2, c3, c4, c5_ew = st.columns([2, 2, 2, 2, 2])
                invoice_no = c1.text_input("Invoice No.", value=def_inv_no)
                invoice_date = c2.date_input("Invoice Date", parse_date(fd.get('invoice_date')))
                eway_bill_no = c5_ew.text_input("E-Way Bill No. (Optional)", fd.get('eway_bill_no',''))
                vendor_code = c3.text_input("Vendor Code", fd.get('vendor_code',''))
                po_no = c4.text_input("P.O. No.", fd.get('po_no',''))
                
                c5, c6, c7, c8 = st.columns(4)
                po_date = c5.date_input("P.O. Date", parse_date(fd.get('po_date')))
                transport_mode = c6.text_input("Transport Mode", fd.get('transport_mode','Road'))
                vehicle_no = c7.text_input("Vehicle No.", fd.get('vehicle_no',''))
                date_of_supply = c8.text_input("Date & Time of Supply", value=fd.get('date_of_supply', def_date_time))

            with st.expander("🏢 Parties Details", expanded=True):
                col_b, col_s = st.columns(2)
                with col_b:
                    st.markdown("**Bill To Party:**")
                    
                    def autofill_inv_party():
                        sel = st.session_state.sel_inv_p_widget
                        if sel != "-- Select Party from Master --":
                            pm = next((p for p in parties_db if p['party_name'] == sel), None)
                            if pm:
                                st.session_state.b1 = pm['party_name']
                                st.session_state.b2 = pm['address']
                                st.session_state.b3 = pm['gstin']
                                st.session_state.b4 = pm['state']
                                st.session_state.b5 = pm['state_code']
                                st.session_state.pos_inv = pm.get('place_of_supply', '')
                        else:
                            for k in ['b1', 'b2', 'b3', 'b4', 'b5', 'pos_inv']: st.session_state[k] = ""

                    sel_p = st.selectbox("Autofill Party Details", party_names, index=default_idx, key="sel_inv_p_widget", on_change=autofill_inv_party)
                        
                    b_name = st.text_input("Name", key="b1")
                    b_add = st.text_area("Address", key="b2", height=68)
                    b_gst = st.text_input("GSTIN", key="b3")
                    c_st1, c_st2, c_st3 = st.columns(3)
                    with c_st1: b_state = st.text_input("State", key="b4")
                    with c_st2: b_scode = st.text_input("State Code", key="b5")
                    with c_st3: place_of_supply = st.text_input("Place of Supply", key="pos_inv")
                
                with col_s:
                    st.markdown("**Shipped To Party:**")
                    
                    if 's1' not in st.session_state:
                        st.session_state.s1 = fd.get('ship_to_name', '')
                        st.session_state.s2 = fd.get('ship_to_address', '')
                        st.session_state.s3 = fd.get('ship_to_gstin', '')
                        st.session_state.s4 = fd.get('ship_to_state', '')
                        st.session_state.s5 = fd.get('ship_to_state_code', '')

                    same_as = st.checkbox("Same as Bill To")
                    if same_as:
                        st.session_state.s1 = st.session_state.b1
                        st.session_state.s2 = st.session_state.b2
                        st.session_state.s3 = st.session_state.b3
                        st.session_state.s4 = st.session_state.b4
                        st.session_state.s5 = st.session_state.b5
                    
                    s_name = st.text_input("Name", key="s1", disabled=same_as)
                    s_add = st.text_area("Address", key="s2", height=68, disabled=same_as)
                    s_gst = st.text_input("GSTIN", key="s3", disabled=same_as)
                    s_state = st.text_input("State", key="s4", disabled=same_as)
                    s_scode = st.text_input("State Code", key="s5", disabled=same_as)

            st.subheader("📦 Item Details")
            if sel_p != "-- Select Party from Master --": items_db = fetch_data("SELECT * FROM item_master WHERE uid=%s AND party_name=%s", (uid, sel_p))
            else: items_db = []
                
            item_opts = ["-- Custom Item --"] + [it['item_description'] for it in items_db]
            
            col_btn1, col_btn2, _ = st.columns([2, 2, 8])
            if col_btn1.button("➕ Add Item"): st.session_state.item_count += 1; st.rerun()
            if col_btn2.button("➖ Remove Item") and st.session_state.item_count > 1: st.session_state.item_count -= 1; st.rerun()

            def autofill_inv_item(index, db):
                sel = st.session_state[f"sel_it_inv_widget_{index}"]
                if sel != "-- Custom Item --":
                    im = next((it for it in db if it['item_description'] == sel), None)
                    if im:
                        st.session_state[f"id_{index}"] = im['item_description']
                        st.session_state[f"ih_{index}"] = im['hsn_code']
                        st.session_state[f"ir_{index}"] = float(im.get('rate', 0.0))

            items_data = []
            for i in range(st.session_state.item_count):
                ex = fi[i] if i < len(fi) else {}
                st.markdown(f"**Item {i+1}**")
                
                if f"id_{i}" not in st.session_state:
                    st.session_state[f"id_{i}"] = ex.get('desc', '')
                    st.session_state[f"ih_{i}"] = ex.get('hsn', '')
                    st.session_state[f"ib_{i}"] = ex.get('boxes', '')
                    st.session_state[f"iq_{i}"] = float(ex.get('qty', 0))
                    st.session_state[f"ir_{i}"] = float(ex.get('rate', 0))

                sel_it = st.selectbox(f"Autofill Item {i+1}", item_opts, key=f"sel_it_inv_widget_{i}", on_change=autofill_inv_item, args=(i, items_db))
                
                c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                with c1: desc = st.text_input("Description", key=f"id_{i}")
                with c2: hsn = st.text_input("HSN Code", key=f"ih_{i}")
                with c3: boxes = st.text_input("Boxes", key=f"ib_{i}")
                with c4: qty = st.number_input("Qty", min_value=0.0, key=f"iq_{i}")
                with c5: rate = st.number_input("Rate (₹)", min_value=0.0, key=f"ir_{i}")
                items_data.append({"desc": desc, "hsn": hsn, "boxes": boxes, "qty": qty, "rate": rate, "amount": qty * rate})
                st.markdown("---")

            tax_type = st.radio("Tax Calculation:", ["CGST + SGST (Intra-state)", "IGST (Inter-state)"], horizontal=True)
            tax_mode = "IGST" if "IGST" in tax_type else "CGST"

            if 'pdf_comp' in st.session_state:
                st.success("✅ Invoice Generated & Saved!")
                c_dl1, c_dl2, c_wa = st.columns([2, 2, 1.5])
                c_dl1.download_button("📄 Download Company Copies (3 Pages)", data=st.session_state['pdf_comp'], file_name=f"TaxInvoice_{st.session_state['inv_no']}_Company.pdf", mime="application/pdf", type="primary")
                c_dl2.download_button("📁 Download Office Copy (1 Page)", data=st.session_state['pdf_off'], file_name=f"TaxInvoice_{st.session_state['inv_no']}_OfficeCopy.pdf", mime="application/pdf")
                
                wa_msg = f"Hello {st.session_state.get('b1', 'Sir/Madam')},%0A%0AHere are your billing details from *{my_company['name']}*:%0A*Invoice No:* {st.session_state['inv_no']}%0A*Amount:* {st.session_state.get('inv_amt', '')}%0A%0AThank you for your business!"
                wa_link = f"https://wa.me/?text={wa_msg}"
                c_wa.link_button("📲 Send on WhatsApp", wa_link)
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

                    current_fd = {
                        'invoice_no': invoice_no, 'invoice_date': invoice_date.strftime('%d/%m/%Y'), 'eway_bill_no': eway_bill_no,
                        'vendor_code': vendor_code, 'po_no': po_no, 'po_date': po_date.strftime('%d/%m/%Y'),
                        'transport_mode': transport_mode, 'vehicle_no': vehicle_no,
                        'date_of_supply': date_of_supply, 'place_of_supply': place_of_supply,
                        'bill_to_name': b_name, 'bill_to_address': b_add, 'bill_to_gstin': b_gst,
                        'bill_to_state': b_state, 'bill_to_state_code': b_scode,
                        'ship_to_name': s_name, 'ship_to_address': s_add, 'ship_to_gstin': s_gst,
                        'ship_to_state': s_state, 'ship_to_state_code': s_scode
                    }

                    if mode == "INSERT": execute_data("""INSERT INTO tax_invoices (created_by, invoice_date, invoice_no, eway_bill_no, vendor_code, po_no, po_date, bill_to_name, bill_to_address, bill_to_gstin, bill_to_state, bill_to_state_code, ship_to_name, ship_to_address, ship_to_gstin, ship_to_state, ship_to_state_code, transport_mode, vehicle_no, date_of_supply, place_of_supply, items_data, amount, tax_type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (safe_name, invoice_date.strftime('%d/%m/%Y'), invoice_no, eway_bill_no, vendor_code, po_no, po_date.strftime('%d/%m/%Y'), b_name, b_add, b_gst, b_state, b_scode, s_name, s_add, s_gst, s_state, s_scode, transport_mode, vehicle_no, date_of_supply, place_of_supply, items_json, f"₹{total_after:.2f}", tax_mode))
                    else: execute_data("""UPDATE tax_invoices SET invoice_date=%s, invoice_no=%s, eway_bill_no=%s, vendor_code=%s, po_no=%s, po_date=%s, bill_to_name=%s, bill_to_address=%s, bill_to_gstin=%s, bill_to_state=%s, bill_to_state_code=%s, ship_to_name=%s, ship_to_address=%s, ship_to_gstin=%s, ship_to_state=%s, ship_to_state_code=%s, transport_mode=%s, vehicle_no=%s, date_of_supply=%s, place_of_supply=%s, items_data=%s, amount=%s, tax_type=%s WHERE id=%s""", (invoice_date.strftime('%d/%m/%Y'), invoice_no, eway_bill_no, vendor_code, po_no, po_date.strftime('%d/%m/%Y'), b_name, b_add, b_gst, b_state, b_scode, s_name, s_add, s_gst, s_state, s_scode, transport_mode, vehicle_no, date_of_supply, place_of_supply, items_json, f"₹{total_after:.2f}", tax_mode, fd['id']))

                    base_css = """<style>@page { size: A4; margin: 10mm 5mm; } body { font-family: Arial, sans-serif; font-size: 11px; color: #000; margin:0; padding:0; } .page-break { page-break-after: always; } .page-container { border: 2px solid #1c2d42; width: 100%; box-sizing: border-box; margin-bottom: 20px; position:relative;} .top-label { position: absolute; top: -15px; right: 5px; font-weight: bold; font-size: 10px; background: #fff; padding: 0 5px;} .container { width: 100%; } .header { text-align: center; border-bottom: 2px solid #1c2d42; padding: 10px; position: relative;} .header-left { position: absolute; top: 10px; left: 10px; text-align: left; } .header-right { position: absolute; top: 10px; right: 10px; text-align: right; } table { width: 100%; border-collapse: collapse; } td, th { border: 1px solid #1c2d42; padding: 4px; vertical-align: top; } .info-table td { border-bottom: 2px solid #1c2d42; border-top: none; } .items-table th { border-top: 2px solid #1c2d42; border-bottom: 2px solid #1c2d42; text-align: center; } .spacer-row td { height: 260px; border-bottom: none; border-top:none;} .footer { padding: 5px 10px; border-top: 2px solid #1c2d42; }</style>"""
                    html_1 = generate_tax_invoice_html(my_company, current_fd, items_data, tax_mode, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, "Original (W)")
                    html_2 = generate_tax_invoice_html(my_company, current_fd, items_data, tax_mode, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, "Duplicate (P)")
                    html_3 = generate_tax_invoice_html(my_company, current_fd, items_data, tax_mode, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, "Triplicate (G)")
                    html_4 = generate_tax_invoice_html(my_company, current_fd, items_data, tax_mode, total_before, cgst, sgst, igst, total_tax, total_after, amt_words, "Office Copy (Y)")

                    full_company_html = f"<!DOCTYPE html><html><head>{base_css}</head><body>{html_1}<div class='page-break'></div>{html_2}<div class='page-break'></div>{html_3}</body></html>"
                    full_office_html = f"<!DOCTYPE html><html><head>{base_css}</head><body>{html_4}</body></html>"
                    
                    st.session_state['pdf_comp'] = HTML(string=full_company_html).write_pdf()
                    st.session_state['pdf_off'] = HTML(string=full_office_html).write_pdf()
                    st.session_state['inv_no'] = invoice_no
                    st.session_state['inv_amt'] = f"₹{total_after:.2f}"
                    st.rerun()

        # ==========================================
        # DELIVERY CHALLAN ENGINE
        # ==========================================
        elif menu == "📝 Delivery Challan":
            st.title("📝 Delivery Challan Engine")
            parties_db = fetch_data("SELECT * FROM party_master WHERE uid=%s", (uid,))
            
            if st.button("🔄 Clear Form (Make New Challan)", key="c_btn"):
                preserve = ["auth_logged_in", "auth_role", "auth_name", "auth_uid", "cookie_manager", "cust_menu", "db_initialized"]
                for k in list(st.session_state.keys()):
                    if k not in preserve: st.session_state.pop(k, None)
                st.session_state.item_count = 1; st.rerun()

            fd = st.session_state.get('form_data', {}); fi = st.session_state.get('form_items', []); mode = st.session_state.get('mode', 'INSERT')
            if 'item_count' not in st.session_state: st.session_state.item_count = 1
            if mode == "UPDATE": st.warning("⚠️ EDITING existing challan.")
            
            def_chal_no = fd.get('challan_no', get_next_auto_no('challans', 'challan_no', safe_name)) if mode == "INSERT" else fd.get('challan_no','')
            def_date_time = get_ist_time()

            dash_party = st.session_state.pop('sel_chal_p', None)
            party_names = ["-- Select Party from Master --"] + [p['party_name'] for p in parties_db]
            default_idx = party_names.index(dash_party) if dash_party in party_names else 0
            
            if dash_party and dash_party != "-- Select Party from Master --":
                pm = next((p for p in parties_db if p['party_name'] == dash_party), None)
                if pm:
                    st.session_state.p_name = pm['party_name']
                    st.session_state.p_add = pm['address']
                    st.session_state.p_gst = pm['gstin']
                    st.session_state.p_state = pm['state']
                    st.session_state.p_scode = pm['state_code']
                    st.session_state.pos_chal = pm.get('place_of_supply', '')
            elif 'p_name' not in st.session_state:
                st.session_state.p_name = fd.get('party_name', '')
                st.session_state.p_add = fd.get('party_address', '')
                st.session_state.p_gst = fd.get('party_gstin', '')
                st.session_state.p_state = fd.get('party_state', '')
                st.session_state.p_scode = fd.get('party_state_code', '')
                st.session_state.pos_chal = fd.get('place_of_supply', '')

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Dispatch To Party Details:**")
                
                def autofill_chal_party():
                    sel = st.session_state.sel_chal_p_widget
                    if sel != "-- Select Party from Master --":
                        pm = next((p for p in parties_db if p['party_name'] == sel), None)
                        if pm:
                            st.session_state.p_name = pm['party_name']
                            st.session_state.p_add = pm['address']
                            st.session_state.p_gst = pm['gstin']
                            st.session_state.p_state = pm['state']
                            st.session_state.p_scode = pm['state_code']
                            st.session_state.pos_chal = pm.get('place_of_supply', '')
                    else:
                        for k in ['p_name', 'p_add', 'p_gst', 'p_state', 'p_scode', 'pos_chal']: st.session_state[k] = ""
                
                sel_p = st.selectbox("Autofill Party Details", party_names, index=default_idx, key="sel_chal_p_widget", on_change=autofill_chal_party)
                        
                party_name = st.text_input("Dispatch To (Party Name)", key="p_name")
                party_address = st.text_area("Party Address", key="p_add")
                party_gstin = st.text_input("Party GSTIN", key="p_gst")
                
                c_st1, c_st2, c_st3 = st.columns(3)
                with c_st1: party_state = st.text_input("Party State", key="p_state")
                with c_st2: party_state_code = st.text_input("State Code", key="p_scode")
                with c_st3: place_of_supply = st.text_input("Place of Supply", key="pos_chal")
                
            with col2:
                st.markdown("**Challan Details:**")
                challan_no = st.text_input("Challan No.", value=def_chal_no, key="c_no")
                eway_bill_no = st.text_input("E-Way Bill No. (Optional)", value=fd.get('eway_bill_no',''), key="ew_no")
                vehicle_no = st.text_input("Vehicle No.", value=fd.get('vehicle_no', ''), key="v_no")
                challan_date = st.date_input("Challan Date", parse_date(fd.get('challan_date')), key="c_date")
                transport_mode = st.text_input("Transport Mode", value=fd.get('transport_mode', 'Road'), key="t_mode")
                date_of_supply = st.text_input("Date & Time of Supply", value=fd.get('date_of_supply', def_date_time))

            st.subheader("📦 Item Details")
            if sel_p != "-- Select Party from Master --": items_db = fetch_data("SELECT * FROM item_master WHERE uid=%s AND party_name=%s", (uid, sel_p))
            else: items_db = []
                
            item_opts = ["-- Custom Item --"] + [it['item_description'] for it in items_db]

            c_btn1, c_btn2, _ = st.columns([2, 2, 8])
            if c_btn1.button("➕ Add Item", key="add_item"): st.session_state.item_count += 1; st.rerun()
            if c_btn2.button("➖ Remove Item", key="rem_item") and st.session_state.item_count > 1: st.session_state.item_count -= 1; st.rerun()

            def autofill_chal_item(index, db):
                sel = st.session_state[f"sel_it_chal_widget_{index}"]
                if sel != "-- Custom Item --":
                    im = next((it for it in db if it['item_description'] == sel), None)
                    if im:
                        st.session_state[f"desc_{index}"] = im['item_description']
                        st.session_state[f"hsn_{index}"] = im['hsn_code']
                        st.session_state[f"rate_{index}"] = float(im.get('rate', 0.0))

            items_data = []
            for i in range(st.session_state.item_count):
                ex = fi[i] if i < len(fi) else {}
                st.markdown(f"**Item {i+1}**")
                
                if f"desc_{i}" not in st.session_state:
                    st.session_state[f"desc_{i}"] = ex.get('desc', '')
                    st.session_state[f"hsn_{i}"] = ex.get('hsn', '')
                    st.session_state[f"box_{i}"] = ex.get('boxes', '')
                    st.session_state[f"qty_{i}"] = float(ex.get('qty', 0))
                    st.session_state[f"rate_{i}"] = float(ex.get('rate', 0))
                
                sel_it = st.selectbox(f"Autofill Item {i+1}", item_opts, key=f"sel_it_chal_widget_{i}", on_change=autofill_chal_item, args=(i, items_db))
                
                c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                with c1: desc = st.text_input("Description", key=f"desc_{i}")
                with c2: hsn = st.text_input("HSN Code", key=f"hsn_{i}")
                with c3: boxes = st.text_input("Boxes", key=f"box_{i}")
                with c4: qty = st.number_input("Qty", min_value=0.0, key=f"qty_{i}")
                with c5: rate = st.number_input("Rate (₹)", min_value=0.0, key=f"rate_{i}")
                items_data.append({"desc": desc, "hsn": hsn, "boxes": boxes, "qty": qty, "rate": rate, "amount": qty * rate})
                st.markdown("---")

            if st.button("🚀 Save & Print Challan", type="primary", key="save_print_btn"):
                total_before = sum(item['amount'] for item in items_data)
                total_tax = (total_before * 0.09) + (total_before * 0.09)
                total_after = total_before + total_tax
                amt_words = num2words(total_after, lang='en_IN').title() + " Only."
                
                if mode == "INSERT": execute_data("""INSERT INTO challans (created_by, challan_date, challan_no, eway_bill_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply, transport_mode, place_of_supply, items_data, amount, is_deleted) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)""", (safe_name, challan_date.strftime('%d/%m/%Y'), challan_no, eway_bill_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply, transport_mode, place_of_supply, json.dumps(items_data), f"₹{total_after:.2f}"))
                else: execute_data("""UPDATE challans SET challan_date=%s, challan_no=%s, eway_bill_no=%s, party_name=%s, party_address=%s, party_gstin=%s, party_state=%s, party_state_code=%s, vehicle_no=%s, date_of_supply=%s, transport_mode=%s, place_of_supply=%s, items_data=%s, amount=%s WHERE id=%s""", (challan_date.strftime('%d/%m/%Y'), challan_no, eway_bill_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply, transport_mode, place_of_supply, json.dumps(items_data), f"₹{total_after:.2f}", fd['id']))
                
                items_html = ""
                for idx, item in enumerate(items_data):
                    qty_display = f"{item['qty']} Pcs" if item['qty'] > 0 else ""
                    items_html += f"<tr><td style='text-align:center;'>{idx+1}.</td><td><strong>{item['desc'].replace(chr(10), '<br>')}</strong></td><td style='text-align:center;'>{item['hsn']}</td><td style='text-align:center;'>{item['boxes']}</td><td style='text-align:center;'>{qty_display}</td><td style='text-align:right;'>{item['rate']:.2f}</td><td style='text-align:right;'>{item['amount']:.2f}</td></tr>"

                eway_row = f"<tr><td style='border:none; border-top: 1px solid #aeb6bf; padding-top: 4px;' colspan='2'><strong>E-Way Bill No:</strong> {eway_bill_no}</td></tr>" if eway_bill_no else ""

                html_content = f"""
                <!DOCTYPE html><html><head><style>
                @page {{ size: A4; margin: 10mm 5mm; }} 
                body {{ font-family: Arial, sans-serif; font-size: 12px; color: #1c2d42; }} 
                .container {{ border: 2px solid #1c2d42; width: 100%; }} 
                .header {{ text-align: center; border-bottom: 2px solid #1c2d42; padding: 15px 10px; background-color: #fcfcfc; position: relative; min-height: 110px; }} 
                .header h2 {{ margin: 0 0 5px 0; color: #1c2d42; font-size: 18px; text-decoration: underline; letter-spacing: 1.5px; font-weight: bold; text-transform: uppercase; }} 
                .header h1 {{ margin: 5px 0; color: #1c2d42; font-size: 32px; line-height: 1.1; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 900; }} 
                .header p {{ margin: 3px 0; font-size: 12px; color: #1c2d42; }} 
                .top-left-info {{ position: absolute; top: 15px; left: 15px; text-align: left; font-size: 12px; color: #1c2d42; line-height: 1.5; }} 
                table {{ width: 100%; border-collapse: collapse; }} 
                td, th {{ border: 1px solid #aeb6bf; padding: 6px; vertical-align: top; }} 
                .items-table th {{ background-color: #e5e8e8; text-align: center; border-bottom: 2px solid #1c2d42; border-top: 2px solid #1c2d42; }} 
                .spacer-row td {{ height: 260px; border-top: none; border-bottom: none; }} 
                .footer {{ padding: 10px; height: 100px; border-top: 2px solid #1c2d42; position: relative; }} 
                .signature {{ position: absolute; right: 20px; bottom: 10px; text-align: center; width: 200px; }}
                </style></head>
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
                                        <tr><td style="border:none; border-top: 1px solid #aeb6bf; padding-top: 4px;"><strong>Date of Supply:</strong> {date_of_supply}</td><td style="border:none; border-top: 1px solid #aeb6bf; border-left: 1px solid #aeb6bf; padding-top: 4px;"><strong>Place of Supply:</strong> {place_of_supply}</td></tr>
                                        {eway_row}
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
                
                st.success("✅ Challan Saved Successfully!")
                c_dl, c_wa = st.columns([2, 2])
                c_dl.download_button(label="📄 Download Ready PDF", data=pdf_c, file_name=f"Challan_{challan_no if challan_no else 'New'}.pdf", mime="application/pdf", type="primary")
                
                wa_msg = f"Hello {party_name},%0A%0AHere are your dispatch details from *{my_company['name']}*:%0A*Challan No:* {challan_no}%0A*Vehicle No:* {vehicle_no}%0A*Amount:* ₹{total_after:.2f}%0A%0AThank you!"
                wa_link = f"https://wa.me/?text={wa_msg}"
                c_wa.link_button("📲 Send on WhatsApp", wa_link)