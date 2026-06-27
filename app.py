import streamlit as st
import extra_streamlit_components as stx
import time
import pandas as pd
from weasyprint import HTML
from num2words import num2words
import datetime
import mysql.connector

st.set_page_config(page_title="Rainbow ERP - Pro SaaS", layout="wide")

# ==========================================
# 1. BULLETPROOF DATABASE FUNCTIONS
# ==========================================
def get_connection():
    """Naya connection banata hai jab bhi zaroorat ho (Crash-Proof)"""
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        connect_timeout=10,
        use_pure=True  # <-- SEGMENTATION FAULT FIX
    )

def init_db():
    """Tables banata hai (sirf pehli baar)"""
    if "db_initialized" not in st.session_state:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # 1. Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    uid VARCHAR(50) PRIMARY KEY,
                    password VARCHAR(50) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    name VARCHAR(100) NOT NULL
                )
            """)
            # 2. Challans Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS challans (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    created_by VARCHAR(100),
                    challan_date VARCHAR(20),
                    challan_no VARCHAR(50),
                    party_name VARCHAR(100),
                    amount VARCHAR(50)
                )
            """)
            # 3. Dynamic Company Profiles Table (Multi-Tenancy SaaS)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_profiles (
                    uid VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    gstin VARCHAR(50),
                    address TEXT,
                    state VARCHAR(50),
                    state_code VARCHAR(20),
                    tagline VARCHAR(200),
                    contact VARCHAR(200),
                    manufacturing VARCHAR(255)
                )
            """)

            # ⚠️ --- TEMPORARY AUTO-CLEAN CODE (START) --- ⚠️
            cursor.execute("TRUNCATE TABLE challans")
            cursor.execute("TRUNCATE TABLE company_profiles")
            cursor.execute("DELETE FROM users WHERE uid != 'boss'")
            # ⚠️ --- TEMPORARY AUTO-CLEAN CODE (END) --- ⚠️
            # Default Master Boss
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO users (uid, password, role, name) VALUES (%s, %s, %s, %s)", 
                               ("boss", "admin123", "superadmin", "Keshav (Master)"))
            conn.commit()
            conn.close()
            st.session_state.db_initialized = True
        except Exception as e:
            st.error(f"DB Init Error: {e}")

init_db()

def fetch_data(query, params=None):
    """Database se data lane ke liye"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        st.error(f"Query Error: {e}")
        return []

def execute_data(query, params):
    """Database mein data save karne ke liye"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except mysql.connector.IntegrityError:
        return "exists"
    except Exception as e:
        st.error(f"Execution Error: {e}")
        return False

def delete_record(table, column, value):
    """Database se record delete karne ke liye"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = f"DELETE FROM {table} WHERE {column} = %s"
        cursor.execute(query, (value,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Delete Error: {e}")
        return False

def get_company_profile(uid):
    """Database se specific company ki profile nikalna (With Rainbow Fallback)"""
    data = fetch_data("SELECT * FROM company_profiles WHERE uid = %s", (uid,))
    if data:
        return data[0]
    else:
        # Default Rainbow Industries configuration if empty
        return {
            "name": "RAINBOW INDUSTRIES",
            "gstin": "09AAAAA0000A1Z1",
            "address": "2804, Dhoom Manikpur, Dadri (G.B. Nagar) U.P. 203207",
            "state": "UP",
            "state_code": "09",
            "tagline": "(An ISO 9001:2015 Certified Company)",
            "contact": "Mob.: 9711325563, 8826366314 | Email: rainbowindustries647@gmail.com",
            "manufacturing": "Manufactures of : Plastic Components, Automobiles, Electricals & Electronics"
        }

# ==========================================
# 2. COOKIE & SESSION MANAGER
# ==========================================
cookie_manager = stx.CookieManager()
time.sleep(0.2)

auth_status, user_role, user_name, user_uid = None, None, None, None
try:
    auth_status = cookie_manager.get(cookie="rainbow_erp_auth")
except Exception: pass
try:
    user_role = cookie_manager.get(cookie="rainbow_user_role")
except Exception: pass
try:
    user_name = cookie_manager.get(cookie="rainbow_user_name")
except Exception: pass
try:
    user_uid = cookie_manager.get(cookie="rainbow_user_uid")
except Exception: pass

if auth_status == "verified":
    st.session_state.auth_logged_in = True
    if user_role and "auth_role" not in st.session_state:
        st.session_state.auth_role = user_role
    if user_name and "auth_name" not in st.session_state:
        st.session_state.auth_name = user_name
    if user_uid and "auth_uid" not in st.session_state:
        st.session_state.auth_uid = user_uid

is_verified = st.session_state.get("auth_logged_in", False)
current_role = st.session_state.get("auth_role", None)
current_name = st.session_state.get("auth_name", None)
current_uid = st.session_state.get("auth_uid", None)

# ==========================================
# 3. LOGIN SCREEN
# ==========================================
if not is_verified:
    st.title("☁️ SaaS ERP Platform")
    _, login_col, _ = st.columns([1, 2, 1])
    with login_col:
        st.subheader("Login to your Account")
        userid = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        if st.button("Secure Login", type="primary", use_container_width=True):
            user_data = fetch_data("SELECT * FROM users WHERE uid = %s AND password = %s", (userid, password))
            if user_data:
                role = user_data[0]["role"]
                name = user_data[0]["name"]
                uid = user_data[0]["uid"]
                
                st.session_state.auth_logged_in = True
                st.session_state.auth_role = role
                st.session_state.auth_name = name
                st.session_state.auth_uid = uid
                
                cookie_manager.set("rainbow_erp_auth", "verified", max_age=2592000, key="set_auth")
                cookie_manager.set("rainbow_user_role", role, max_age=2592000, key="set_role")
                cookie_manager.set("rainbow_user_name", name, max_age=2592000, key="set_name")
                cookie_manager.set("rainbow_user_uid", uid, max_age=2592000, key="set_uid")
                
                st.success(f"✅ Login Verified! Welcome {name}...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Invalid Credentials!")

# ==========================================
# 4. LOGGED IN SYSTEM (DASHBOARD)
# ==========================================
else:
    # ⚠️ SMART SYNC FIX: Agar purani aadhi cookie milegi, toh auto-reset karke bahar nikal dega
    if not current_role or not current_uid:
        st.warning("⚠️ System Update: Old session found. Resetting... Please wait.")
        cookie_manager.delete("rainbow_erp_auth", key="force_logout")
        if "auth_logged_in" in st.session_state: del st.session_state.auth_logged_in
        time.sleep(1.5)
        st.rerun()
    else:
        safe_name = current_name if current_name else "User"
        safe_role = current_role.upper()

        st.sidebar.title("☁️ ERP System")
        st.sidebar.markdown(f"**Welcome:** {safe_name}")
        st.sidebar.markdown(f"**Role:** {safe_role}")
        st.sidebar.markdown("---")
        
        if st.sidebar.button("🔒 Logout"):
            if "auth_logged_in" in st.session_state: del st.session_state.auth_logged_in
            if "auth_role" in st.session_state: del st.session_state.auth_role
            if "auth_name" in st.session_state: del st.session_state.auth_name
            if "auth_uid" in st.session_state: del st.session_state.auth_uid
            
            cookie_manager.delete("rainbow_erp_auth", key="del_auth")
            cookie_manager.delete("rainbow_user_role", key="del_role")
            cookie_manager.delete("rainbow_user_name", key="del_name")
            cookie_manager.delete("rainbow_user_uid", key="del_uid")
            st.success("Logging out...")
            time.sleep(0.5)
            st.rerun()

        # Fetch current dynamic company profile from database
        my_company = get_company_profile(current_uid)

        # ----------------------------------------
        # A. SUPER ADMIN PANEL
        # ----------------------------------------
        if safe_role == "SUPERADMIN":
            st.title("👑 Super Admin Dashboard (MySQL Live)")
            
            all_users = fetch_data("SELECT * FROM users")
            total_clients = sum(1 for u in all_users if u['role'] == 'customer')
            
            challan_count_data = fetch_data("SELECT COUNT(*) as count FROM challans")
            total_bills = challan_count_data[0]['count'] if challan_count_data else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric(label="Total Registered Clients", value=str(total_clients))
            m2.metric(label="Simulated Monthly Revenue", value=f"₹{total_clients * 2499}")
            m3.metric(label="Platform Total Bills", value=str(total_bills))
            
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
                        if new_uid and new_pass and new_fullname:
                            result = execute_data("INSERT INTO users (uid, password, role, name) VALUES (%s, %s, %s, %s)", 
                                                  (new_uid, new_pass, new_role_select, new_fullname))
                            if result == "exists":
                                st.error("❌ Yeh Login ID pehle se exist karti hai!")
                            elif result:
                                st.success(f"✅ Account Created! ID: '{new_uid}'")
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.error("⚠️ Kripya saari fields ko bharein!")

            with col_right:
                st.subheader("👥 Live User Database")
                st.dataframe(pd.DataFrame(all_users), use_container_width=True)
                
                st.markdown("---")
                st.subheader("🗑️ Delete User (Danger Zone)")
                del_uid = st.text_input("Enter User ID (UID) to delete")
                if st.button("🗑️ Delete User", type="primary"):
                    if del_uid == "boss":
                        st.error("❌ Cannot delete the Master Admin (boss)!")
                    elif del_uid:
                        if delete_record("users", "uid", del_uid):
                            st.success(f"✅ User '{del_uid}' has been permanently deleted!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("User not found or delete failed.")
            
            st.markdown("---")
            st.subheader("📜 Live Platform Challan Monitor")
            all_challans = fetch_data("SELECT id, created_by, challan_date, challan_no, party_name, amount FROM challans ORDER BY id DESC")
            if not all_challans:
                st.info("ℹ️ Abhi tak kisi ne challan nahi banaya hai.")
            else:
                st.dataframe(pd.DataFrame(all_challans), use_container_width=True)

        # ----------------------------------------
        # B. CUSTOMER / CLIENT ERP PANEL
        # ----------------------------------------
        elif safe_role == "CUSTOMER":
            selected_module = st.sidebar.radio("Menu", ["📝 Make New Challan", "📜 Challan History", "⚙️ Company Profile"])
            
            if selected_module == "⚙️ Company Profile":
                st.title("⚙️ Dynamic Company Profile Settings")
                st.info("Yahan jo details aap bherenge, wo PDF Invoice Header layout mein bilkul fit ho jayengi.")
                
                c_name = st.text_input("Company/Factory Name", value=my_company["name"])
                c_tagline = st.text_input("Tagline / ISO Text (e.g., An ISO 9001:2015 Certified Company)", value=my_company.get("tagline", ""))
                c_gst = st.text_input("GSTIN Number", value=my_company["gstin"])
                c_address = st.text_area("Registered Address", value=my_company["address"])
                
                col_s1, col_s2 = st.columns(2)
                with col_s1: c_state = st.text_input("State", value=my_company["state"])
                with col_s2: c_state_code = st.text_input("State Code", value=my_company["state_code"])
                
                c_contact = st.text_input("Contact Lines (e.g., Mob.: 9711325563 | Email: ...)", value=my_company.get("contact", ""))
                c_manufacturing = st.text_input("Business Scope (e.g., Manufactures of : Plastic Components...)", value=my_company.get("manufacturing", ""))
                
                if st.button("💾 Save Profile Permanently to Database", type="primary"):
                    saved = execute_data("""
                        INSERT INTO company_profiles (uid, name, gstin, address, state, state_code, tagline, contact, manufacturing)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE 
                        name=%s, gstin=%s, address=%s, state=%s, state_code=%s, tagline=%s, contact=%s, manufacturing=%s
                    """, (current_uid, c_name, c_gst, c_address, c_state, c_state_code, c_tagline, c_contact, c_manufacturing,
                          c_name, c_gst, c_address, c_state, c_state_code, c_tagline, c_contact, c_manufacturing))
                    
                    if saved:
                        st.success("✅ Profile Updated Live in MySQL Database!")
                        time.sleep(1)
                        st.rerun()

            elif selected_module == "📜 Challan History":
                st.title("📜 My Challan History Register")
                user_challans = fetch_data("SELECT id, challan_date, challan_no, party_name, amount FROM challans WHERE created_by = %s ORDER BY id DESC", (safe_name,))
                
                if not user_challans:
                    st.info("ℹ️ Abhi tak koi challan generate nahi kiya gaya hai.")
                else:
                    st.dataframe(pd.DataFrame(user_challans), use_container_width=True)
                    
                    st.markdown("---")
                    st.subheader("🗑️ Delete Challan")
                    del_id = st.number_input("Enter Challan 'id' to delete", min_value=0, step=1)
                    if st.button("🗑️ Delete this Challan", type="primary"):
                        if del_id > 0:
                            if delete_record("challans", "id", del_id):
                                st.success(f"✅ Challan ID {del_id} deleted permanently!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to delete challan.")

            elif selected_module == "📝 Make New Challan":
                st.title("📝 Delivery Challan Generator")
                
                if 'item_count' not in st.session_state:
                    st.session_state.item_count = 1

                if st.button("🔄 Naya Challan Banayein (Clear Data)"):
                    st.session_state.item_count = 1
                    st.rerun()

                st.subheader("Party & Challan Details")
                col1, col2 = st.columns(2)

                with col1:
                    party_name = st.text_input("Dispatch To (Party Name)", value="")
                    party_address = st.text_area("Party Address", value="")
                    party_gstin = st.text_input("Party GSTIN", value="")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1: party_state = st.text_input("Party State", value="")
                    with col_p2: party_state_code = st.text_input("Party State Code", value="")
                    
                with col2:
                    challan_no = st.text_input("Challan No.", value="")
                    vehicle_no = st.text_input("Vehicle No.", value="")
                    date_of_supply = st.date_input("Date of Supply", datetime.date.today())
                    challan_date = st.date_input("Challan Date", datetime.date.today())
                    transport_mode = st.text_input("Transport Mode", value="Road")
                    place_of_supply = st.text_input("Place of Supply", value="")

                st.markdown("---")
                st.subheader("Item Details")

                col_btn1, col_btn2, _ = st.columns([2, 2, 8])
                with col_btn1:
                    if st.button("➕ Add Another Item"): st.session_state.item_count += 1
                with col_btn2:
                    if st.button("➖ Remove Last Item"): 
                        if st.session_state.item_count > 1: st.session_state.item_count -= 1

                items_data = []
                for i in range(st.session_state.item_count):
                    st.markdown(f"**Item {i+1}**")
                    c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
                    with c1: desc = st.text_area(f"Description", key=f"desc_{i}", height=68)
                    with c2: hsn = st.text_input(f"HSN", key=f"hsn_{i}")
                    with c3: boxes = st.text_input(f"Boxes", key=f"box_{i}")
                    with c4: qty = st.number_input(f"Qty", min_value=0, step=1, key=f"qty_{i}")
                    with c5: rate = st.number_input(f"Rate", min_value=0.0, step=0.1, key=f"rate_{i}")
                    
                    items_data.append({
                        "desc": desc, "hsn": hsn, "boxes": boxes, "qty": qty, "rate": rate, "amount": qty * rate
                    })

                st.markdown("---")
                submit = st.button("🚀 Generate Challan PDF & Save", type="primary", use_container_width=True)

                if submit:
                    total_amount_before_tax = sum(item['amount'] for item in items_data)
                    cgst = total_amount_before_tax * 0.09
                    sgst = total_amount_before_tax * 0.09
                    total_tax = cgst + sgst
                    total_amount = total_amount_before_tax + total_tax
                    amt_str = f"₹{total_amount:.2f}"
                    
                    saved = execute_data("""
                        INSERT INTO challans (created_by, challan_date, challan_no, party_name, amount) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (safe_name, challan_date.strftime('%d/%m/%Y'), challan_no, party_name, amt_str))
                    
                    if not saved:
                        st.error("⚠️ Failed to save in DB, but generating PDF anyway...")
                    
                    items_html = ""
                    for idx, item in enumerate(items_data):
                        qty_display = f"{item['qty']} Pcs" if item['qty'] > 0 else ""
                        items_html += f"""
                        <tr>
                            <td style="text-align:center;">{idx+1}.</td>
                            <td><strong>{item['desc'].replace(chr(10), '<br>')}</strong></td>
                            <td style="text-align:center;">{item['hsn']}</td>
                            <td style="text-align:center;">{item['boxes']}</td>
                            <td style="text-align:center;">{qty_display}</td>
                            <td style="text-align:right;">{item['rate']:.2f}</td>
                            <td style="text-align:right;">{item['amount']:.2f}</td>
                        </tr>
                        """
                        
                    amount_in_words = num2words(total_amount, lang='en_IN').title() + " Only." if total_amount > 0 else ""
                    
                    # 100% Dynamic HTML Content with Exact Match Layout
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
                                <tr class="spacer-row">
                                    <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
                                </tr>
                            </table>

                            <table style="border-top: 2px solid #1c2d42;">
                                <tr>
                                    <td rowspan="5" style="width:60%; padding-left:10px;">
                                        <strong>Total Amount in Words:</strong><br>
                                        <em>{amount_in_words}</em>
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
                                    <p>For <strong>{my_company['name'].upper()}</strong></p>
                                    <br><br>
                                    <p style="border-top:1px solid #000; font-size:10px;">Authorised Signature</p>
                                </div>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    
                    pdf_path = f"Challan_{challan_no if challan_no else 'New'}.pdf"
                    HTML(string=html_content).write_pdf(pdf_path)
                    
                    if saved:
                        st.success("✅ Challan Generated & Saved to MySQL Database!")
                    
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_file,
                            file_name=pdf_path,
                            mime="application/pdf"
                        )