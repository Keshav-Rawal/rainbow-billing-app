import streamlit as st
from weasyprint import HTML
from num2words import num2words
import datetime

st.set_page_config(page_title="Rainbow Industries ERP Module", layout="wide")

# --- Login Session State Manage ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 1. Login Screen ---
if not st.session_state.logged_in:
    st.title("🔒 Rainbow Industries ERP Module")
    
    _, login_col, _ = st.columns([1, 2, 1])
    
    with login_col:
        st.subheader("Authorized Access Only")
        userid = st.text_input("User ID", value="")
        password = st.text_input("Password", type="password", value="")
        login_submit = st.button("Login & Open ERP", type="primary", use_container_width=True)
        
        if login_submit:
            if userid == "admin" and password == "rainbow786": 
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Galat User ID ya Password! Kripya sahi details dalein.")

# --- 2. Main ERP System ---
else:
    # Sidebar Navigation Menu (Tabs)
    st.sidebar.title("🌈 Rainbow ERP")
    st.sidebar.markdown("---")
    
    selected_module = st.sidebar.radio(
        "Navigation Menu",
        ["📦 Delivery Challan", "📊 Future Modules"]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔒 Logout From ERP"):
        st.session_state.logged_in = False
        st.rerun()

    # ==========================================
    # MODULE 1: DELIVERY CHALLAN
    # ==========================================
    if selected_module == "📦 Delivery Challan":
        st.title("Rainbow Industries ERP Module")
        st.header("📝 Delivery Challan Generator")

        # Initialize session state for dynamic items
        if 'item_count' not in st.session_state:
            st.session_state.item_count = 1

        st.subheader("Party & Challan Details")
        col1, col2 = st.columns(2)

        with col1:
            party_name = st.text_input("Dispatch To (Party Name)", value="")
            party_address = st.text_area("Party Address", value="")
            party_gstin = st.text_input("Party GSTIN", value="")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                party_state = st.text_input("Party State", value="")
            with col_p2:
                party_state_code = st.text_input("Party State Code", value="")
                
        with col2:
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                challan_no = st.text_input("Challan No.", value="")
                vehicle_no = st.text_input("Vehicle No.", value="")
                date_of_supply = st.date_input("Date of Supply", datetime.date.today())
            with col_c2:
                challan_date = st.date_input("Challan Date", datetime.date.today())
                transport_mode = st.text_input("Transport Mode", value="Road")
                place_of_supply = st.text_input("Place of Supply", value="")
            
            st.markdown("---")
            owner_gstin = st.text_input("Rainbow Industries GSTIN", value="")
            col_st1, col_st2 = st.columns(2)
            with col_st1:
                state_name = st.text_input("My State", value="UP")
            with col_st2:
                state_code = st.text_input("My State Code", value="09")

        st.markdown("---")
        st.subheader("Item Details")

        # Buttons to add/remove items
        col_btn1, col_btn2, _ = st.columns([2, 2, 8])
        with col_btn1:
            if st.button("➕ Add Another Item"):
                st.session_state.item_count += 1
        with col_btn2:
            if st.button("➖ Remove Last Item"):
                if st.session_state.item_count > 1:
                    st.session_state.item_count -= 1

        # Dynamic item rows
        items_data = []
        for i in range(st.session_state.item_count):
            st.markdown(f"**Item {i+1}**")
            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1.5])
            with c1:
                desc = st.text_area(f"Description", key=f"desc_{i}", height=68)
            with c2:
                hsn = st.text_input(f"HSN", key=f"hsn_{i}")
            with c3:
                boxes = st.text_input(f"Boxes", key=f"box_{i}")
            with c4:
                qty = st.number_input(f"Qty", min_value=0, step=1, key=f"qty_{i}")
            with c5:
                rate = st.number_input(f"Rate", min_value=0.0, step=0.1, key=f"rate_{i}")
            
            items_data.append({
                "desc": desc, "hsn": hsn, "boxes": boxes, "qty": qty, "rate": rate, "amount": qty * rate
            })

        st.markdown("---")
        submit = st.button("🚀 Generate Challan PDF", type="primary", use_container_width=True)

        # --- Processing & PDF Generation ---
        if submit:
            total_amount_before_tax = sum(item['amount'] for item in items_data)
            cgst = total_amount_before_tax * 0.09
            sgst = total_amount_before_tax * 0.09
            total_tax = cgst + sgst
            total_amount = total_amount_before_tax + total_tax
            
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
                
            if total_amount > 0:
                amount_in_words = num2words(total_amount, lang='en_IN').title() + " Only."
            else:
                amount_in_words = ""
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <style>
                @page {{ size: A4; margin: 15mm; }}
                body {{ font-family: Arial, sans-serif; font-size: 12px; color: #333; }}
                .container {{ border: 2px solid #2c3e50; width: 100%; }}
                .header {{ text-align: center; border-bottom: 2px solid #2c3e50; padding: 15px 10px; background-color: #f8f9fa; position: relative; }}
                .header h1 {{ margin: 5px 0; color: #2c3e50; font-size: 26px; line-height: 1.2; }}
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
                            <strong>GSTIN:</strong> {owner_gstin}<br>
                            <strong>State:</strong> {state_name}<br>
                            <strong>Code:</strong> {state_code}
                        </div>
                        <h2>DELIVERY CHALLAN</h2>
                        <h1>RAINBOW INDUSTRIES</h1>
                        <p>(An ISO 9001:2015 Certified Company)</p>
                        <p>2804, Dhoom Manikpur, Dadri (G.B. Nagar) U.P. 203207</p>
                        <p>Mob.: 9711325563, 8826366314 | Email: rainbowindustries647@gmail.com</p>
                        <p><strong>Manufactures of : Plastic Components, Automobiles, Electricals & Electronics</strong></p>
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
                            <p>For <strong>RAINBOW INDUSTRIES</strong></p>
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
            
            st.success("✅ Challan Successfully Generated!")
            
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_file,
                    file_name=pdf_path,
                    mime="application/pdf"
                )

    # ==========================================
    # MODULE 2: FUTURE MODULES (Coming Soon)
    # ==========================================
    elif selected_module == "📊 Future Modules":
        st.title("Rainbow Industries ERP Module")
        st.header("🚧 Coming Soon...")
        