import streamlit as st
import extra_streamlit_components as stx
import time
import pandas as pd
from weasyprint import HTML
from num2words import num2words
import datetime

st.set_page_config(page_title="Rainbow ERP - SaaS Edition", layout="wide")

# --- Cookie Manager Setup ---
cookie_manager = stx.CookieManager()
time.sleep(0.1)

auth_status = cookie_manager.get(cookie="rainbow_erp_auth")
user_role = cookie_manager.get(cookie="rainbow_user_role")
user_name = cookie_manager.get(cookie="rainbow_user_name")

# --- Dummy Users Database ---
USERS_DB = {
    "boss": {"pass": "admin123", "role": "superadmin", "name": "Keshav (Master)"},
    "partner": {"pass": "partner123", "role": "superadmin", "name": "Manager"},
    "client": {"pass": "client123", "role": "customer", "name": "Demo User Factory"}
}

# --- Temporary Session Memory ---
if 'challan_history' not in st.session_state:
    st.session_state.challan_history = []
if 'company_profile' not in st.session_state:
    st.session_state.company_profile = {
        "name": "Rainbow Industries",
        "gstin": "09AAAAA0000A1Z1",
        "address": "2804, Dhoom Manikpur, Dadri (G.B. Nagar) U.P. 203207",
        "state": "UP",
        "state_code": "09"
    }

# --- 1. LOGIN SCREEN ---
if auth_status != "verified":
    st.title("☁️ SaaS ERP Platform")
    _, login_col, _ = st.columns([1, 2, 1])
    
    with login_col:
        st.subheader("Login to your Account")
        userid = st.text_input("User ID", value="")
        password = st.text_input("Password", type="password", value="")
        login_submit = st.button("Secure Login", type="primary", use_container_width=True)
        
        if login_submit:
            if userid in USERS_DB and USERS_DB[userid]["pass"] == password:
                role = USERS_DB[userid]["role"]
                name = USERS_DB[userid]["name"]
                
                # NAYA: Unique keys ke sath cookies save ho rahi hain
                cookie_manager.set("rainbow_erp_auth", "verified", max_age=2592000, key="set_auth")
                cookie_manager.set("rainbow_user_role", role, max_age=2592000, key="set_role")
                cookie_manager.set("rainbow_user_name", name, max_age=2592000, key="set_name")
                
                st.success(f"✅ Login Verified! Welcome {name}...")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Invalid Credentials!")

# --- 2. LOGGED IN SYSTEM ---
else:
    # NAYA: Safe variables taaki AttributeError na aaye
    safe_name = user_name if user_name else "User"
    safe_role = user_role.upper() if user_role else "GUEST"

    st.sidebar.title("☁️ ERP System")
    st.sidebar.markdown(f"**Welcome:** {safe_name}")
    st.sidebar.markdown(f"**Role:** {safe_role}")
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🔒 Logout"):
        # NAYA: Unique keys ke sath cookies delete ho rahi hain
        cookie_manager.delete("rainbow_erp_auth", key="del_auth")
        cookie_manager.delete("rainbow_user_role", key="del_role")
        cookie_manager.delete("rainbow_user_name", key="del_name")
        st.success("Logging out...")
        time.sleep(0.5)
        st.rerun()

    # ==========================================
    # SUPER ADMIN PANEL
    # ==========================================
    if safe_role == "SUPERADMIN":
        st.title("👑 Super Admin Dashboard")
        m1, m2, m3 = st.columns(3)
        m1.metric(label="Total Active Clients", value="142", delta="+3 this week")
        m2.metric(label="Monthly Revenue", value="₹42,500", delta="+15%")
        m3.metric(label="Platform Total Bills", value=str(8432 + len(st.session_state.challan_history)))
        
        st.markdown("---")
        st.subheader("👥 Client Management")
        client_data = pd.DataFrame({
            "Client ID": ["CLI-001", "CLI-002", "CLI-003"],
            "Company Name": ["A.K. Plastics", "Demo Factory", "Sharma Traders"],
            "Plan": ["Pro (₹2499/yr)", "Free Trial", "Pro (₹2499/yr)"],
            "Status": ["Active", "Active", "Suspended"]
        })
        st.dataframe(client_data, use_container_width=True)

    # ==========================================
    # CUSTOMER ERP (With History & PDF)
    # ==========================================
    elif safe_role == "CUSTOMER":
        selected_module = st.sidebar.radio("Menu", ["📝 Make New Challan", "📜 Challan History", "⚙️ Company Profile"])
        
        if selected_module == "⚙️ Company Profile":
            st.title("⚙️ Company Profile Settings")
            st.info("SaaS Module: Yahan aapki factory ki details save hoti hain jo PDF par print hongi.")
            
            c_name = st.text_input("Company Name", value=st.session_state.company_profile["name"])
            c_gst = st.text_input("GSTIN Number", value=st.session_state.company_profile["gstin"])
            c_address = st.text_area("Registered Address", value=st.session_state.company_profile["address"])
            col_s1, col_s2 = st.columns(2)
            with col_s1: c_state = st.text_input("State", value=st.session_state.company_profile["state"])
            with col_s2: c_state_code = st.text_input("State Code", value=st.session_state.company_profile["state_code"])
            
            if st.button("💾 Save Profile", type="primary"):
                st.session_state.company_profile = {
                    "name": c_name, "gstin": c_gst, "address": c_address, "state": c_state, "state_code": c_state_code
                }
                st.success("✅ Profile Updated Successfully!")

        elif selected_module == "📜 Challan History":
            st.title("📜 Challan History Register")
            
            if len(st.session_state.challan_history) == 0:
                st.info("ℹ️ Abhi tak koi challan generate nahi kiya gaya hai.")
            else:
                df_history = pd.DataFrame(st.session_state.challan_history)
                st.dataframe(df_history, use_container_width=True)

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
            submit = st.button("🚀 Generate Challan PDF", type="primary", use_container_width=True)

            if submit:
                total_amount_before_tax = sum(item['amount'] for item in items_data)
                cgst = total_amount_before_tax * 0.09
                sgst = total_amount_before_tax * 0.09
                total_tax = cgst + sgst
                total_amount = total_amount_before_tax + total_tax
                
                # --- Save to History ---
                new_record = {
                    "Date": challan_date.strftime('%d/%m/%Y'),
                    "Challan No": challan_no,
                    "Party Name": party_name,
                    "Amount": f"₹{total_amount:.2f}"
                }
                st.session_state.challan_history.append(new_record)
                
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
                
                # Fetching details from Profile module
                my_company = st.session_state.company_profile
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                    @page {{ size: A4; margin: 15mm; }}
                    body {{ font-family: Arial, sans-serif; font-size: 12px; color: #333; }}
                    .container {{ border: 2px solid #2c3e50; width: 100%; }}
                    .header {{ text-align: center; border-bottom: 2px solid #2c3e50; padding: 15px 10px; background-color: #f8f9fa; position: relative; }}
                    .header h1 {{ margin: 5px 0; color: #2c3e50; font-size: 26px; line-height: 1.2; text-transform: uppercase; }}
                    .header h2 {{ margin: 0 0 5px 0; color: #2c3e50; font-size: 18px; text-decoration: underline; letter-spacing: 1px; }}
                    .header p {{ margin: 3px 0; font-size: 11px; }}
                    .top-left-info {{ position: absolute; top: 15px; left: 15px; text-align: left; font-size: 11px; color: #555; line-height: 1.4; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    td, th {{ border: 1px solid #aeb6bf; padding: 6px; vertical-align: top; }}
                    .items-table th {{ background-color: #e5e8e8; text-align: center; border-bottom: 2px solid #2c3e50; border-top: 2px solid #2c3e50; }}
                    .spacer-row td {{ height: 150px; border-top: none; border-bottom: none; }}
                    .footer {{ padding: 10px; height: 100px; border-top: 2px solid #2c3e50; background-color: #f8f9fa; position: relative; }}
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
                            <p>{my_company['address']}</p>
                        </div>
                        <table>
                            <tr>
                                <td style="width: 50%; border-right: 2px solid #2c3e50;">
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

                        <table style="border-top: 2px solid #2c3e50;">
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
                
                st.success("✅ Challan Generated & Saved in History!")
                
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="📄 Download PDF",
                        data=pdf_file,
                        file_name=pdf_path,
                        mime="application/pdf"
                    )