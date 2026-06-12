import streamlit as st
from weasyprint import HTML
from num2words import num2words
import datetime

st.set_page_config(page_title="Rainbow Industries - Billing", layout="wide")

st.title("Rainbow Industries - Delivery Challan Generator")

# --- Input Form ---
with st.form("challan_form"):
    st.subheader("Party & Challan Details")
    col1, col2 = st.columns(2)
    
    with col1:
        party_name = st.text_input("Dispatch To (Party Name)", value="MATERIAL MOVELL INDIA PVT LTD")
        party_address = st.text_area("Party Address", value="G-86/1 INDUSTRIAL AREA SITE-5, Kasna, Greater Noida (U.P)")
        party_gstin = st.text_input("Party GSTIN", value="09AACCM2525P1Z")
    
    with col2:
        challan_no = st.text_input("Challan No.", value="006")
        challan_date = st.date_input("Date", datetime.date.today())
        vehicle_no = st.text_input("Vehicle No.", value="UP16 DC 9834")

    st.subheader("Item Details")
    item_desc = st.text_input("Product Description", value="BASE PLATE\nJob work only for ED coating")
    hsn_code = st.text_input("HSN Code", value="7323")
    boxes = st.text_input("No of Box", value="02 Box")
    qty_str = st.text_input("Total Qty (e.g., 2500 Pcs)", value="2500 Pcs")
    
    # Calculation inputs
    qty_calc = st.number_input("Quantity (for calculation)", value=2500, min_value=1)
    rate = st.number_input("Approx. Rate", value=5.00, min_value=0.0)
    
    submit = st.form_submit_button("Generate Challan")

# --- Processing & PDF Generation ---
if submit:
    # Calculations
    amount = qty_calc * rate
    cgst = amount * 0.09
    sgst = amount * 0.09
    total_amount = amount + cgst + sgst
    
    # Convert total to words
    amount_in_words = num2words(total_amount, lang='en_IN').title() + " Only."
    
    # HTML Template with f-strings for dynamic data
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        @page {{ size: A4; margin: 15mm; }}
        body {{ font-family: Arial, sans-serif; font-size: 12px; color: #333; }}
        .container {{ border: 2px solid #2c3e50; width: 100%; }}
        .header {{ text-align: center; border-bottom: 2px solid #2c3e50; padding: 15px 10px; background-color: #f8f9fa; }}
        .header h1 {{ margin: 5px 0; color: #2c3e50; font-size: 26px; }}
        .header p {{ margin: 3px 0; font-size: 11px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td, th {{ border: 1px solid #aeb6bf; padding: 6px; vertical-align: top; }}
        .items-table th {{ background-color: #e5e8e8; text-align: center; border-bottom: 2px solid #2c3e50; border-top: 2px solid #2c3e50; }}
        .items-table td {{ height: 250px; }}
        .footer {{ padding: 10px; height: 100px; border-top: 2px solid #2c3e50; background-color: #f8f9fa; position: relative; }}
        .signature {{ position: absolute; right: 20px; bottom: 10px; text-align: center; width: 200px; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
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
                        <strong>GSTIN:</strong> {party_gstin}
                    </td>
                    <td style="width: 50%; padding: 0;">
                        <table style="border:none;">
                            <tr>
                                <td style="border:none;"><strong>Challan No:</strong> {challan_no}</td>
                                <td style="border:none;"><strong>Date:</strong> {challan_date.strftime('%d/%m/%Y')}</td>
                            </tr>
                            <tr>
                                <td style="border:none; border-top: 1px solid #aeb6bf;" colspan="2">
                                    <strong>Vehicle:</strong> {vehicle_no}<br>
                                </td>
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
                <tr>
                    <td style="text-align:center;">1.</td>
                    <td><strong>{item_desc.replace(chr(10), '<br>')}</strong></td>
                    <td style="text-align:center;">{hsn_code}</td>
                    <td style="text-align:center;">{boxes}</td>
                    <td style="text-align:center;">{qty_str}</td>
                    <td style="text-align:right;">{rate:.2f}</td>
                    <td style="text-align:right;">{amount:.2f}</td>
                </tr>
            </table>

            <table style="border-top: 2px solid #2c3e50;">
                <tr>
                    <td rowspan="3" style="width:60%; padding-left:10px;">
                        <strong>Total Amount in Words:</strong><br>
                        <em>{amount_in_words}</em>
                    </td>
                    <td style="width:20%; text-align:right; background-color:#f8f9fa;">Total Before Tax</td>
                    <td style="width:20%; text-align:right;">{amount:.2f}</td>
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
                    <td style="background-color:#f8f9fa;"></td>
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
    
    # Generate PDF
    pdf_path = f"Challan_{challan_no}.pdf"
    HTML(string=html_content).write_pdf(pdf_path)
    
    st.success("✅ Challan Successfully Generated!")
    
    # Provide download button
    with open(pdf_path, "rb") as pdf_file:
        st.download_button(
            label="📄 Download PDF",
            data=pdf_file,
            file_name=pdf_path,
            mime="application/pdf"
        )