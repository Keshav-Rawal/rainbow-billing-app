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
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("CREATE TABLE IF NOT EXISTS users (uid VARCHAR(50) PRIMARY KEY, password VARCHAR(50) NOT NULL, role VARCHAR(20) NOT NULL, name VARCHAR(100) NOT NULL)")
            cursor.execute("CREATE TABLE IF NOT EXISTS company_profiles (uid VARCHAR(50) PRIMARY KEY, name VARCHAR(100) NOT NULL, gstin VARCHAR(50), address TEXT, state VARCHAR(50), state_code VARCHAR(20), tagline VARCHAR(200), contact VARCHAR(200), manufacturing VARCHAR(255))")
            
            cursor.execute("CREATE TABLE IF NOT EXISTS challans (id INT)") 
            cursor.execute("SHOW COLUMNS FROM challans LIKE 'items_data'")
            if not cursor.fetchone():
                cursor.execute("DROP TABLE IF EXISTS challans")
                cursor.execute("""
                    CREATE TABLE challans (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        created_by VARCHAR(100),
                        challan_date VARCHAR(20),
                        challan_no VARCHAR(50),
                        party_name VARCHAR(100),
                        party_address TEXT,
                        party_gstin VARCHAR(50),
                        party_state VARCHAR(50),
                        party_state_code VARCHAR(20),
                        vehicle_no VARCHAR(50),
                        date_of_supply VARCHAR(20),
                        transport_mode VARCHAR(50),
                        place_of_supply VARCHAR(100),
                        items_data TEXT,
                        amount VARCHAR(50),
                        is_deleted INT DEFAULT 0,
                        deleted_at DATETIME NULL
                    )
                """)
            else:
                try: cursor.execute("ALTER TABLE challans ADD COLUMN is_deleted INT DEFAULT 0")
                except: pass
                try: cursor.execute("ALTER TABLE challans ADD COLUMN deleted_at DATETIME NULL")
                except: pass
            
            try: cursor.execute("DELETE FROM challans WHERE is_deleted = 1 AND deleted_at < NOW() - INTERVAL 30 DAY")
            except: pass

            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users (uid, password, role, name) VALUES (%s, %s, %s, %s)", ("boss", "admin123", "superadmin", "Keshav (Master)"))
            
            conn.commit()
            cursor.close()
            conn.close()
            st.session_state.db_initialized = True
        except Exception as e:
            pass

init_db()

def fetch_data(query, params=None):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    except Exception as e:
        return []

def execute_data(query, params):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        return False

def get_company_profile(uid):
    data = fetch_data("SELECT * FROM company_profiles WHERE uid = %s", (uid,))
    if data: return data[0]
    return {"name": "RAINBOW INDUSTRIES", "gstin": "09AAAAA0000A1Z1", "address": "2804, Dhoom Manikpur, Dadri (G.B. Nagar) U.P. 203207", "state": "UP", "state_code": "09", "tagline": "(An ISO 9001:2015 Certified Company)", "contact": "Mob.: 9711325563, 8826366314 | Email: rainbowindustries647@gmail.com", "manufacturing": "Manufactures of : Plastic Components, Automobiles, Electricals & Electronics"}

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
        auth = cookie_manager.get(cookie="rainbow_erp_auth")
        if auth == "verified":
            st.session_state.auth_logged_in = True
            st.session_state.auth_role = cookie_manager.get(cookie="rainbow_user_role")
            st.session_state.auth_name = cookie_manager.get(cookie="rainbow_user_name")
            st.session_state.auth_uid = cookie_manager.get(cookie="rainbow_user_uid")
        else:
            st.session_state.auth_logged_in = False
    except:
        st.session_state.auth_logged_in = False

is_verified = st.session_state.get("auth_logged_in", False)
current_role = st.session_state.get("auth_role", None)
current_name = st.session_state.get("auth_name", None)
current_uid = st.session_state.get("auth_uid", None)

# Initialize Menu State dynamically for Smart Redirects
if "cust_menu" not in st.session_state:
    st.session_state.cust_menu = "📝 Make / Edit Challan"

# ==========================================
# 3. LOGIN SCREEN
# ==========================================
if not is_verified:
    st.title("☁️ SaaS ERP Platform")
    _, login_col, _ = st.columns([1, 2, 1])
    with login_col:
        st.subheader("Login to your Account")
        userid = st.text_input("User ID", key="login_id")
        password = st.text_input("Password", type="password", key="login_pwd")
        if st.button("Secure Login", key="login_btn"):
            user_data = fetch_data("SELECT * FROM users WHERE uid = %s AND password = %s", (userid, password))
            if user_data:
                st.session_state.auth_logged_in = True
                st.session_state.auth_role = user_data[0]["role"]
                st.session_state.auth_name = user_data[0]["name"]
                st.session_state.auth_uid = user_data[0]["uid"]
                cookie_manager.set("rainbow_erp_auth", "verified", max_age=2592000, key=f"set_auth_{userid}")
                cookie_manager.set("rainbow_user_role", user_data[0]["role"], max_age=2592000, key=f"set_role_{userid}")
                cookie_manager.set("rainbow_user_name", user_data[0]["name"], max_age=2592000, key=f"set_name_{userid}")
                cookie_manager.set("rainbow_user_uid", user_data[0]["uid"], max_age=2592000, key=f"set_uid_{userid}")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Invalid Credentials!")

# ==========================================
# 4. LOGGED IN SYSTEM (DASHBOARD)
# ==========================================
else:
    if not current_role or not current_uid:
        st.session_state.auth_logged_in = False
        st.rerun()
    else:
        safe_name = current_name if current_name else "User"
        safe_role = current_role.upper()

        st.sidebar.title("☁️ ERP System")
        st.sidebar.markdown(f"**Welcome:** {safe_name}")
        st.sidebar.markdown(f"**Role:** {safe_role}")
        st.sidebar.markdown("---")
        
        if st.sidebar.button("🔒 Logout", key="logout_sidebar"):
            for key in ["auth_logged_in", "auth_role", "auth_name", "auth_uid", "form_data", "form_items", "mode", "cust_menu"]:
                if key in st.session_state: del st.session_state[key]
            try:
                cookie_manager.delete("rainbow_erp_auth", key="del_a")
                cookie_manager.delete("rainbow_user_role", key="del_r")
                cookie_manager.delete("rainbow_user_name", key="del_n")
                cookie_manager.delete("rainbow_user_uid", key="del_u")
            except: pass
            time.sleep(0.5)
            st.rerun()

        my_company = get_company_profile(current_uid)

        # ----------------------------------------
        # A. SUPER ADMIN PANEL
        # ----------------------------------------
        if safe_role == "SUPERADMIN":
            st.title("👑 Super Admin Dashboard")
            all_users = fetch_data("SELECT * FROM users")
            total_clients = sum(1 for u in all_users if u['role'] == 'customer')
            challan_count_data = fetch_data("SELECT COUNT(*) as count FROM challans WHERE is_deleted = 0")
            total_bills = challan_count_data[0]['count'] if challan_count_data else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Clients", str(total_clients))
            m2.metric("Monthly Revenue", f"₹{total_clients * 2499}")
            m3.metric("Platform Active Bills", str(total_bills))
            
            st.markdown("---")
            col_left, col_right = st.columns([1, 1])
            with col_left:
                st.subheader("➕ Create New Account")
                with st.form("create_user_form", clear_on_submit=True):
                    new_uid = st.text_input("Username / Login ID")
                    new_pass = st.text_input("Password", type="password")
                    new_fullname = st.text_input("Full Name / Factory Name")
                    new_role_select = st.selectbox("Role", ["customer", "superadmin"])
                    if st.form_submit_button("🚀 Create Account Live"):
                        if execute_data("INSERT INTO users (uid, password, role, name) VALUES (%s, %s, %s, %s)", (new_uid, new_pass, new_role_select, new_fullname)):
                            st.success("Account Created!"); time.sleep(0.5); st.rerun()

            with col_right:
                st.subheader("👥 Live User Database")
                st.dataframe(pd.DataFrame(all_users), width="stretch")
            
            st.markdown("---")
            st.subheader("📜 Live Platform Challan Monitor (Active)")
            all_challans = fetch_data("SELECT id, created_by, challan_date, challan_no, party_name, amount FROM challans WHERE is_deleted = 0 ORDER BY id DESC LIMIT 50")
            if all_challans: st.dataframe(pd.DataFrame(all_challans), width="stretch")
            else: st.info("No active challans yet.")

        # ----------------------------------------
        # B. CUSTOMER / CLIENT ERP PANEL
        # ----------------------------------------
        elif safe_role == "CUSTOMER":
            selected_module = st.sidebar.radio("Menu", ["📝 Make / Edit Challan", "📜 Challan History", "🗑️ Recycle Bin", "⚙️ Company Profile"], key="cust_menu")
            
            if selected_module == "⚙️ Company Profile":
                st.title("⚙️ Dynamic Company Profile")
                c_name = st.text_input("Company/Factory Name", value=my_company["name"], key="c_name")
                c_tagline = st.text_input("Tagline (e.g., An ISO 9001:2015 Certified)", value=my_company.get("tagline", ""), key="c_tagline")
                c_gst = st.text_input("GSTIN Number", value=my_company["gstin"], key="c_gst")
                c_address = st.text_area("Registered Address", value=my_company["address"], key="c_address")
                col_s1, col_s2 = st.columns(2)
                with col_s1: c_state = st.text_input("State", value=my_company["state"], key="c_state")
                with col_s2: c_state_code = st.text_input("State Code", value=my_company["state_code"], key="c_scode")
                c_contact = st.text_input("Contact Lines", value=my_company.get("contact", ""), key="c_contact")
                c_manufacturing = st.text_input("Business Scope", value=my_company.get("manufacturing", ""), key="c_manu")
                
                if st.button("💾 Save Profile", type="primary", key="save_profile"):
                    execute_data("""
                        INSERT INTO company_profiles (uid, name, gstin, address, state, state_code, tagline, contact, manufacturing)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE name=%s, gstin=%s, address=%s, state=%s, state_code=%s, tagline=%s, contact=%s, manufacturing=%s
                    """, (current_uid, c_name, c_gst, c_address, c_state, c_state_code, c_tagline, c_contact, c_manufacturing,
                          c_name, c_gst, c_address, c_state, c_state_code, c_tagline, c_contact, c_manufacturing))
                    st.success("Profile Updated!"); time.sleep(0.5); st.rerun()

            # --- SMART HISTORY TAB WITH INLINE BUTTONS ---
            elif selected_module == "📜 Challan History":
                st.title("📜 My Challan History")
                user_challans = fetch_data("SELECT id, challan_date, challan_no, party_name, amount FROM challans WHERE created_by = %s AND is_deleted = 0 ORDER BY id DESC LIMIT 50", (safe_name,))
                
                if user_challans:
                    st.markdown("---")
                    # Table Headers
                    h1, h2, h3, h4, h5, h6 = st.columns([1, 1.5, 1.5, 3, 2, 2])
                    h1.write("**ID**"); h2.write("**Date**"); h3.write("**Challan No**"); h4.write("**Party Name**"); h5.write("**Amount**"); h6.write("**Actions**")
                    st.markdown("---")
                    
                    # Table Rows
                    for c in user_challans:
                        c1, c2, c3, c4, c5, c6_edit, c6_del = st.columns([1, 1.5, 1.5, 3, 2, 1, 1])
                        c1.write(f"#{c['id']}")
                        c2.write(c['challan_date'])
                        c3.write(c['challan_no'])
                        c4.write(c['party_name'])
                        c5.write(c['amount'])
                        
                        # Inline Edit Button
                        if c6_edit.button("✏️", key=f"edit_{c['id']}", help="Edit this Challan"):
                            full_data = fetch_data("SELECT * FROM challans WHERE id=%s", (c['id'],))
                            if full_data:
                                st.session_state.form_data = full_data[0]
                                try:
                                    st.session_state.form_items = json.loads(full_data[0]['items_data'])
                                    st.session_state.item_count = len(st.session_state.form_items)
                                except:
                                    st.session_state.form_items = []
                                    st.session_state.item_count = 1
                                st.session_state.mode = "UPDATE"
                                st.session_state.cust_menu = "📝 Make / Edit Challan" # Smart Redirect
                                st.rerun()
                                
                        # Inline Delete Button
                        if c6_del.button("🗑️", key=f"del_{c['id']}", help="Move to Recycle Bin"):
                            if execute_data("UPDATE challans SET is_deleted = 1, deleted_at = NOW() WHERE id = %s", (c['id'],)):
                                st.rerun()
                else: 
                    st.info("No active challans found.")

            # --- SMART RECYCLE BIN TAB WITH INLINE RESTORE ---
            elif selected_module == "🗑️ Recycle Bin":
                st.title("🗑️ Recycle Bin")
                st.info("⚠️ Items yahan 30 din tak rahenge, uske baad automatically permanently delete ho jayenge.")
                
                deleted_challans = fetch_data("SELECT id, challan_date, challan_no, party_name, amount, DATE_FORMAT(deleted_at, '%d-%m-%Y %H:%i') as deleted_on FROM challans WHERE created_by = %s AND is_deleted = 1 ORDER BY id DESC LIMIT 50", (safe_name,))
                
                if deleted_challans:
                    st.markdown("---")
                    # Table Headers
                    h1, h2, h3, h4, h5, h6 = st.columns([1, 1.5, 1.5, 2.5, 1.5, 2])
                    h1.write("**ID**"); h2.write("**Challan No**"); h3.write("**Deleted On**"); h4.write("**Party Name**"); h5.write("**Amount**"); h6.write("**Action**")
                    st.markdown("---")
                    
                    # Table Rows
                    for c in deleted_challans:
                        c1, c2, c3, c4, c5, c6 = st.columns([1, 1.5, 1.5, 2.5, 1.5, 2])
                        c1.write(f"#{c['id']}")
                        c2.write(c['challan_no'])
                        c3.write(c['deleted_on'])
                        c4.write(c['party_name'])
                        c5.write(c['amount'])
                        
                        if c6.button("🔄 Restore", key=f"res_{c['id']}", help="Restore to History"):
                            if execute_data("UPDATE challans SET is_deleted = 0, deleted_at = NULL WHERE id = %s", (c['id'],)): 
                                st.rerun()
                else:
                    st.success("Recycle bin ekdum khali hai!")

            # --- UNIFIED FORM (Redirects here on Edit) ---
            elif selected_module == "📝 Make / Edit Challan":
                st.title("📝 Delivery Challan Engine")
                
                if st.button("🔄 Clear Form (Start New)", key="c_btn"):
                    for key in ["form_data", "form_items", "mode"]:
                        if key in st.session_state: del st.session_state[key]
                    st.session_state.item_count = 1
                    st.rerun()

                fd = st.session_state.get('form_data', {})
                fi = st.session_state.get('form_items', [])
                mode = st.session_state.get('mode', 'INSERT')

                if 'item_count' not in st.session_state: st.session_state.item_count = 1

                st.markdown("---")
                if mode == "UPDATE": 
                    st.warning(f"⚠️ You are EDITING an existing challan (ID: #{fd.get('id', '')}). Save changes below.")
                
                col1, col2 = st.columns(2)
                with col1:
                    party_name = st.text_input("Dispatch To (Party Name)", value=fd.get('party_name', ''), key="p_name")
                    party_address = st.text_area("Party Address", value=fd.get('party_address', ''), key="p_add")
                    party_gstin = st.text_input("Party GSTIN", value=fd.get('party_gstin', ''), key="p_gst")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1: party_state = st.text_input("Party State", value=fd.get('party_state', ''), key="p_state")
                    with col_p2: party_state_code = st.text_input("Party State Code", value=fd.get('party_state_code', ''), key="p_scode")
                    
                with col2:
                    challan_no = st.text_input("Challan No.", value=fd.get('challan_no', ''), key="c_no")
                    vehicle_no = st.text_input("Vehicle No.", value=fd.get('vehicle_no', ''), key="v_no")
                    date_of_supply = st.date_input("Date of Supply", parse_date(fd.get('date_of_supply')), key="d_sup")
                    challan_date = st.date_input("Challan Date", parse_date(fd.get('challan_date')), key="c_date")
                    transport_mode = st.text_input("Transport Mode", value=fd.get('transport_mode', 'Road'), key="t_mode")
                    place_of_supply = st.text_input("Place of Supply", value=fd.get('place_of_supply', ''), key="p_sup")

                st.markdown("---")
                st.subheader("Item Details")

                col_btn1, col_btn2, _ = st.columns([2, 2, 8])
                with col_btn1:
                    if st.button("➕ Add Another Item", key="add_item"): st.session_state.item_count += 1; st.rerun()
                with col_btn2:
                    if st.button("➖ Remove Last Item", key="rem_item") and st.session_state.item_count > 1: st.session_state.item_count -= 1; st.rerun()

                items_data = []
                for i in range(st.session_state.item_count):
                    st.markdown(f"**Item {i+1}**")
                    existing_item = fi[i] if i < len(fi) else {}
                    c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                    with c1: desc = st.text_area("Description", value=existing_item.get('desc', ''), key=f"desc_{i}", height=68)
                    with c2: hsn = st.text_input("HSN", value=existing_item.get('hsn', ''), key=f"hsn_{i}")
                    with c3: boxes = st.text_input("Boxes", value=existing_item.get('boxes', ''), key=f"box_{i}")
                    with c4: qty = st.number_input("Qty", value=float(existing_item.get('qty', 0)), min_value=0.0, step=1.0, key=f"qty_{i}")
                    with c5: rate = st.number_input("Rate", value=float(existing_item.get('rate', 0.0)), min_value=0.0, step=0.1, key=f"rate_{i}")
                    
                    items_data.append({"desc": desc, "hsn": hsn, "boxes": boxes, "qty": qty, "rate": rate, "amount": qty * rate})

                st.markdown("---")
                btn_txt = "🔄 Update Existing Challan & Print" if mode == "UPDATE" else "🚀 Save New Challan & Print"
                
                if st.button(btn_txt, type="primary", key="save_print_btn"):
                    total_amount_before_tax = sum(item['amount'] for item in items_data)
                    cgst = total_amount_before_tax * 0.09
                    sgst = total_amount_before_tax * 0.09
                    total_tax = cgst + sgst
                    total_amount = total_amount_before_tax + total_tax
                    amt_str = f"₹{total_amount:.2f}"
                    items_json = json.dumps(items_data)

                    saved = False
                    if mode == "INSERT":
                        saved = execute_data("""
                            INSERT INTO challans (created_by, challan_date, challan_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply, transport_mode, place_of_supply, items_data, amount, is_deleted) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
                        """, (safe_name, challan_date.strftime('%d/%m/%Y'), challan_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply.strftime('%d/%m/%Y'), transport_mode, place_of_supply, items_json, amt_str))
                    elif mode == "UPDATE":
                        saved = execute_data("""
                            UPDATE challans SET challan_date=%s, challan_no=%s, party_name=%s, party_address=%s, party_gstin=%s, party_state=%s, party_state_code=%s, vehicle_no=%s, date_of_supply=%s, transport_mode=%s, place_of_supply=%s, items_data=%s, amount=%s 
                            WHERE id=%s
                        """, (challan_date.strftime('%d/%m/%Y'), challan_no, party_name, party_address, party_gstin, party_state, party_state_code, vehicle_no, date_of_supply.strftime('%d/%m/%Y'), transport_mode, place_of_supply, items_json, amt_str, fd['id']))

                    if saved: st.success(f"✅ Challan {mode}D Successfully in Database!")
                    else: st.error("⚠️ Failed to save in DB, generating PDF anyway...")
                    
                    items_html = ""
                    for idx, item in enumerate(items_data):
                        qty_display = f"{item['qty']} Pcs" if item['qty'] > 0 else ""
                        items_html += f"<tr><td style='text-align:center;'>{idx+1}.</td><td><strong>{item['desc'].replace(chr(10), '<br>')}</strong></td><td style='text-align:center;'>{item['hsn']}</td><td style='text-align:center;'>{item['boxes']}</td><td style='text-align:center;'>{qty_display}</td><td style='text-align:right;'>{item['rate']:.2f}</td><td style='text-align:right;'>{item['amount']:.2f}</td></tr>"
                        
                    amount_in_words = num2words(total_amount, lang='en_IN').title() + " Only." if total_amount > 0 else ""
                    
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                    <style>
                        @page {{ size: A4; margin: 15mm; }}
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
                        .spacer-row td {{ height: 150px; border-top: none; border-bottom: none; }}
                        .footer {{ padding: 10px; height: 100px; border-top: 2px solid #1c2d42; background-color: #f8f9fa; position: relative; }}
                        .signature {{ position: absolute; right: 20px; bottom: 10px; text-align: center; width: 200px; }}
                    </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header">
                                <div class="top-left-info">
                                    <strong>GSTIN:</strong> {my_company['gstin']}<br>
                                    <strong>State:</strong> {my_company['state']}<br>
                                    <strong>Code:</strong> {my_company['state_code']}
                                </div>
                                <h2>DELIVERY CHALLAN</h2>
                                <h1>{my_company['name']}</h1>
                                <p>{my_company['tagline']}</p>
                                <p>{my_company['address']}</p>
                                <p>{my_company['contact']}</p>
                                <p style="font-weight: bold; font-size: 13px; margin-top: 5px;">{my_company['manufacturing']}</p>
                            </div>
                            <table>
                                <tr>
                                    <td style="width: 50%; border-right: 2px solid #1c2d42;">
                                        <strong>Dispatch To:</strong><br>
                                        <strong>{party_name}</strong><br>
                                        {party_address.replace(chr(10), '<br>')}<br>
                                        <strong>GSTIN:</strong> {party_gstin}<br>
                                        <strong>State:</strong> {party_state} &nbsp;&nbsp;&nbsp; <strong>Code:</strong> {party_state_code}
                                    </td>
                                    <td style="width: 50%; padding: 0;">
                                        <table style="border:none; width: 100%;">
                                            <tr>
                                                <td style="border:none; width: 50%; padding-bottom: 4px;"><strong>Challan No:</strong> {challan_no}</td>
                                                <td style="border:none; border-left: 1px solid #aeb6bf; width: 50%; padding-bottom: 4px;"><strong>Date:</strong> {challan_date.strftime('%d/%m/%Y')}</td>
                                            </tr>
                                            <tr>
                                                <td style="border:none; border-top: 1px solid #aeb6bf; padding-top: 4px; padding-bottom: 4px;"><strong>Vehicle:</strong> {vehicle_no}</td>
                                                <td style="border:none; border-top: 1px solid #aeb6bf; border-left: 1px solid #aeb6bf; padding-top: 4px; padding-bottom: 4px;"><strong>Transport Mode:</strong> {transport_mode}</td>
                                            </tr>
                                            <tr>
                                                <td style="border:none; border-top: 1px solid #aeb6bf; padding-top: 4px;"><strong>Date of Supply:</strong> {date_of_supply.strftime('%d/%m/%Y')}</td>
                                                <td style="border:none; border-top: 1px solid #aeb6bf; border-left: 1px solid #aeb6bf; padding-top: 4px;"><strong>Place of Supply:</strong> {place_of_supply}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <table class="items-table">
                                <tr>
                                    <th style="width:5%;">S.No</th>
                                    <th style="width:35%;">Product Description</th>
                                    <th style="width:10%;">HSN Code</th>
                                    <th style="width:10%;">No of Box</th>
                                    <th style="width:10%;">Total Qty</th>
                                    <th style="width:12%;">Approx. Rate</th>
                                    <th style="width:18%;">Approx. Amount</th>
                                </tr>
                                {items_html}
                                <tr class="spacer-row"><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
                            </table>

                            <table style="border-top: 2px solid #1c2d42;">
                                <tr>
                                    <td rowspan="5" style="width:60%; padding-left:10px;">
                                        <strong>Total Amount in Words:</strong><br><em>{amount_in_words}</em>
                                    </td>
                                    <td style="width:20%; text-align:right; background-color:#f8f9fa;">Total Before Tax</td>
                                    <td style="width:20%; text-align:right;">{total_amount_before_tax:.2f}</td>
                                </tr>
                                <tr>
                                    <td style="text-align:right; background-color:#f8f9fa;">Add: CGST @ 9%</td>
                                    <td style="text-align:right;">{cgst:.2f}</td>
                                </tr>
                                <tr>
                                    <td style="text-align:right; background-color:#f8f9fa;">Add: SGST @ 9%</td>
                                    <td style="text-align:right;">{sgst:.2f}</td>
                                </tr>
                                <tr>
                                    <td style="text-align:right; background-color:#f8f9fa; font-weight:bold;">Total Amount of Tax</td>
                                    <td style="text-align:right; font-weight:bold;">{total_tax:.2f}</td>
                                </tr>
                                <tr>
                                    <td style="text-align:right; font-weight:bold; background-color:#e5e8e8;">Total After Tax</td>
                                    <td style="text-align:right; font-weight:bold; background-color:#e5e8e8;">{total_amount:.2f}</td>
                                </tr>
                            </table>

                            <div class="footer">
                                <p style="font-size: 10px;">Certified That The Particulars given Above are true and correct.</p>
                                <div class="signature">
                                    <p>For <strong>{my_company['name'].upper()}</strong></p><br><br>
                                    <p style="border-top:1px solid #000; font-size:10px;">Authorised Signature</p>
                                </div>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    pdf_filename = f"Challan_{challan_no if challan_no else 'New'}.pdf"
                    HTML(string=html_content).write_pdf(pdf_filename)
                    
                    with open(pdf_filename, "rb") as pdf_file:
                        st.download_button(label="📄 Download Ready PDF", data=pdf_file, file_name=pdf_filename, mime="application/pdf", key=f"dl_pdf_{uuid.uuid4()}")