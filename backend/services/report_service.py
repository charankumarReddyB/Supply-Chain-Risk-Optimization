import os
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from backend.models.database import execute_query

# NumberedCanvas helper to add "Page X of Y" and header/footer
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Don't draw header/footer on page 1 (cover page)
        if self._pageNumber == 1:
            self.restoreState()
            return
            
        # Draw Header
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1A365D"))
        self.drawString(54, 750, "SUPPLY CHAIN RISK ANALYSIS & OPTIMIZATION REPORT")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        self.drawRightString(558, 750, datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 742, 558, 742)
        
        # Draw Footer
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        self.drawString(54, 45, "Confidential - B.Tech Capstone Project")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 45, page_text)
        self.line(54, 58, 558, 58)
        
        self.restoreState()

class ReportService:
    @staticmethod
    def generate_excel_report(output_path):
        """Generates a multi-sheet Excel report with supply chain metrics."""
        # Query Data for different sheets
        
        # 1. Dashboard summary
        summary_query = """
            SELECT 
                COUNT(DISTINCT Order_ID) as Total_Orders,
                SUM(Quantity) as Total_Items_Sold,
                ROUND(SUM(Sales), 2) as Total_Revenue,
                ROUND(SUM(Profit), 2) as Total_Profit,
                ROUND(AVG(Delivery_Delay), 2) as Avg_Delivery_Delay_Days,
                SUM(CASE WHEN Risk_Level = 'High' THEN 1 ELSE 0 END) as High_Risk_Orders
            FROM fact_order
        """
        df_summary = pd.DataFrame(execute_query(summary_query))
        
        # 2. Supplier performance
        supplier_query = """
            SELECT 
                s.Supplier_Name as Supplier_Name,
                s.Supplier_Rating as Rating,
                s.Supplier_Status as Status,
                COUNT(f.Fact_ID) as Total_Orders,
                ROUND(SUM(f.Sales), 2) as Total_Sales,
                ROUND(AVG(f.Delivery_Delay), 2) as Avg_Delay_Days,
                SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) as High_Risk_Orders
            FROM dim_supplier s
            LEFT JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
            GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating, s.Supplier_Status
            ORDER BY Rating DESC
        """
        df_supplier = pd.DataFrame(execute_query(supplier_query))
        
        # 3. Inventory Reorder Alerts
        inventory_query = """
            SELECT 
                p.product_id as Product_ID,
                p.product_name as Product_Name,
                w.name as Warehouse_Name,
                i.stock_level as Current_Stock,
                i.reorder_point as Reorder_Point,
                i.safety_stock as Safety_Stock,
                i.lead_time_days as Lead_Time_Days,
                (i.reorder_point + i.safety_stock - i.stock_level) as Recommended_Reorder_Qty
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN warehouses w ON i.warehouse_id = w.warehouse_id
            WHERE i.stock_level <= i.reorder_point
            ORDER BY i.stock_level ASC
        """
        df_inventory = pd.DataFrame(execute_query(inventory_query))
        
        # 4. High Risk Orders
        risk_query = """
            SELECT 
                f.Order_ID,
                c.Customer_Fname as Cust_First_Name,
                c.Customer_Lname as Cust_Last_Name,
                p.Product_Name,
                f.Sales,
                f.Profit,
                f.Delivery_Delay as Delay_Days,
                f.Risk_Level
            FROM fact_order f
            JOIN dim_customer c ON f.Customer_ID = c.Customer_ID
            JOIN dim_product p ON f.Product_ID = p.Product_ID
            WHERE f.Risk_Level = 'High'
            ORDER BY f.Profit ASC
        """
        df_risk = pd.DataFrame(execute_query(risk_query))
        
        # Save to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name="Summary", index=False)
            df_supplier.to_excel(writer, sheet_name="Supplier Performance", index=False)
            df_inventory.to_excel(writer, sheet_name="Inventory Alerts", index=False)
            df_risk.to_excel(writer, sheet_name="High Risk Orders", index=False)
            
        print(f"Excel report generated at: {output_path}")
        return output_path

    @staticmethod
    def generate_pdf_report(output_path):
        """Generates a professional PDF report with supply chain analysis."""
        # 1. Fetch Summary Statistics
        stats_query = """
            SELECT 
                COUNT(DISTINCT Order_ID) as Total_Orders,
                SUM(Quantity) as Total_Items,
                ROUND(SUM(Sales), 2) as Revenue,
                ROUND(SUM(Profit), 2) as Profit,
                ROUND(AVG(Delivery_Delay), 2) as Avg_Delay,
                SUM(CASE WHEN Risk_Level = 'High' THEN 1 ELSE 0 END) as High_Risk_Count,
                SUM(CASE WHEN Risk_Level = 'Medium' THEN 1 ELSE 0 END) as Med_Risk_Count,
                SUM(CASE WHEN Risk_Level = 'Low' THEN 1 ELSE 0 END) as Low_Risk_Count
            FROM fact_order
        """
        stats = execute_query(stats_query)[0]
        
        # 2. Fetch Top Delayed Suppliers
        supplier_query = """
            SELECT 
                s.Supplier_Name as name,
                s.Supplier_Rating as rating,
                ROUND(AVG(f.Delivery_Delay), 2) as avg_delay,
                COUNT(f.Fact_ID) as orders_count
            FROM dim_supplier s
            JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
            GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating
            ORDER BY avg_delay DESC
            LIMIT 5
        """
        suppliers = execute_query(supplier_query)
        
        # 3. Fetch Urgent Inventory Replenishments
        inventory_query = """
            SELECT 
                p.product_name,
                w.name as warehouse,
                i.stock_level,
                i.reorder_point,
                (i.reorder_point + i.safety_stock - i.stock_level) as reorder_qty
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN warehouses w ON i.warehouse_id = w.warehouse_id
            WHERE i.stock_level <= i.reorder_point
            ORDER BY i.stock_level ASC
            LIMIT 5
        """
        inventory_items = execute_query(inventory_query)

        # Set up ReportLab Document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        
        # Custom styles matching rich design
        style_title = ParagraphStyle(
            'CoverTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=26,
            leading=32,
            textColor=colors.HexColor("#1A365D"),
            spaceAfter=12
        )
        
        style_subtitle = ParagraphStyle(
            'CoverSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=30
        )
        
        style_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=15,
            spaceAfter=10,
            keepWithNext=True
        )
        
        style_body = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#2D3748")
        )
        
        style_table_header = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.white
        )
        
        style_table_cell = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#2D3748")
        )

        story = []
        
        # --- COVER PAGE ---
        story.append(Spacer(1, 150))
        story.append(Paragraph("SUPPLY CHAIN RISK ANALYSIS & OPTIMIZATION", style_title))
        story.append(Paragraph("Comprehensive Backend Analytical & Optimization Report", style_subtitle))
        
        # Horizontal line
        line_data = [[""]]
        line_table = Table(line_data, colWidths=[504])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0,0), (-1,-1), 3, colors.HexColor("#3182CE")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 150))
        
        # Metadata block
        metadata_text = f"""
        <b>Prepared For:</b> B.Tech Capstone Project Evaluators<br/>
        <b>Date:</b> {datetime.now().strftime("%B %d, %Y")}<br/>
        <b>System:</b> Analytical Engine (MySQL Data Warehouse & ML Models)<br/>
        """
        story.append(Paragraph(metadata_text, style_body))
        story.append(PageBreak())
        
        # --- PAGE 2: EXECUTIVE SUMMARY & STATS ---
        story.append(Paragraph("Executive Summary Dashboard", style_heading))
        story.append(Paragraph(
            "This report highlights the performance and risk profile of the supply chain network. "
            "Data was extracted from the DataCo Smart Supply Chain transactional database, cleaned, transformed, "
            "and populated into a Star Schema Data Warehouse. Below are the key KPI metrics.",
            style_body
        ))
        story.append(Spacer(1, 15))
        
        # KPI Table Grid
        kpi_data = [
            [
                Paragraph("<b>Total Orders Analyzed</b>", style_body),
                Paragraph(f"{stats['Total_Orders']:,}", style_body),
                Paragraph("<b>Total Revenue</b>", style_body),
                Paragraph(f"${stats['Revenue']:,.2f}", style_body)
            ],
            [
                Paragraph("<b>Total Profit</b>", style_body),
                Paragraph(f"${stats['Profit']:,.2f}", style_body),
                Paragraph("<b>Avg Delivery Delay</b>", style_body),
                Paragraph(f"{stats['Avg_Delay']:.2f} Days", style_body)
            ],
            [
                Paragraph("<b>High Risk Orders</b>", style_body),
                Paragraph(f"<font color='red'><b>{stats['High_Risk_Count']}</b></font>", style_body),
                Paragraph("<b>Low Risk Orders</b>", style_body),
                Paragraph(f"<font color='green'><b>{stats['Low_Risk_Count']}</b></font>", style_body)
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[140, 112, 140, 112])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 20))
        
        # --- DELAYED SUPPLIERS ---
        story.append(Paragraph("Supplier Delay Analysis (Top 5 Delayed)", style_heading))
        story.append(Paragraph(
            "The following suppliers have the highest average delivery delay. Strategic reviews are suggested "
            "for those with ratings below 3.5 or delays exceeding 2 days.",
            style_body
        ))
        story.append(Spacer(1, 10))
        
        supplier_table_data = [[
            Paragraph("Supplier Name", style_table_header),
            Paragraph("Rating", style_table_header),
            Paragraph("Average Delay (Days)", style_table_header),
            Paragraph("Total Shipments", style_table_header)
        ]]
        for s in suppliers:
            # Color code ratings
            rating_text = f"<font color='red'><b>{s['rating']:.2f}</b></font>" if s['rating'] < 3.5 else f"{s['rating']:.2f}"
            supplier_table_data.append([
                Paragraph(s['name'], style_table_cell),
                Paragraph(rating_text, style_table_cell),
                Paragraph(f"{s['avg_delay']:.2f}", style_table_cell),
                Paragraph(str(s['orders_count']), style_table_cell)
            ])
            
        supplier_table = Table(supplier_table_data, colWidths=[200, 80, 120, 104])
        supplier_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B6CB0")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(supplier_table)
        story.append(Spacer(1, 20))
        
        # --- INVENTORY REPLENISHMENT ---
        story.append(Paragraph("Inventory Replenishment Triggers", style_heading))
        story.append(Paragraph(
            "The following products have dropped below their reorder points. Replenishment orders should be placed "
            "immediately with the recommended quantities to prevent stockouts.",
            style_body
        ))
        story.append(Spacer(1, 10))
        
        inv_table_data = [[
            Paragraph("Product Name", style_table_header),
            Paragraph("Warehouse", style_table_header),
            Paragraph("Current Stock", style_table_header),
            Paragraph("Reorder Point", style_table_header),
            Paragraph("Reorder Qty", style_table_header)
        ]]
        for item in inventory_items:
            inv_table_data.append([
                Paragraph(item['product_name'], style_table_cell),
                Paragraph(item['warehouse'], style_table_cell),
                Paragraph(str(item['stock_level']), style_table_cell),
                Paragraph(str(item['reorder_point']), style_table_cell),
                Paragraph(f"<b>{item['reorder_qty']}</b>", style_table_cell)
            ])
            
        inv_table = Table(inv_table_data, colWidths=[180, 110, 74, 70, 70])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C5282")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(inv_table)
        
        # Build Document
        doc.build(story, canvasmaker=NumberedCanvas)
        print(f"PDF report generated at: {output_path}")
        return output_path

    @staticmethod
    def generate_risk_summary_pdf(output_path):
        """Generates a focused Risk Summary PDF report with distribution table."""
        risk_data = execute_query("""
            SELECT
                Risk_Level,
                COUNT(*) AS Count,
                ROUND(SUM(Sales), 2) AS Total_Revenue,
                ROUND(SUM(Profit), 2) AS Total_Profit,
                ROUND(AVG(Delivery_Delay), 2) AS Avg_Delay,
                ROUND(COUNT(*) / (SELECT COUNT(*) FROM fact_order) * 100, 2) AS Percentage
            FROM fact_order
            GROUP BY Risk_Level
            ORDER BY FIELD(Risk_Level, 'High', 'Medium', 'Low')
        """)

        doc = SimpleDocTemplate(output_path, pagesize=letter,
                                rightMargin=54, leftMargin=54, topMargin=72, bottomMargin=72)
        styles = getSampleStyleSheet()

        style_heading = ParagraphStyle('H', parent=styles['Heading2'], fontName='Helvetica-Bold',
                                       fontSize=16, textColor=colors.HexColor("#2B6CB0"),
                                       spaceBefore=15, spaceAfter=10)
        style_body = ParagraphStyle('B', parent=styles['Normal'], fontName='Helvetica',
                                    fontSize=10, leading=14, textColor=colors.HexColor("#2D3748"))
        style_th = ParagraphStyle('TH', parent=styles['Normal'], fontName='Helvetica-Bold',
                                   fontSize=9, textColor=colors.white)
        style_td = ParagraphStyle('TD', parent=styles['Normal'], fontName='Helvetica',
                                   fontSize=9, textColor=colors.HexColor("#2D3748"))

        story = [
            Paragraph("Risk Summary Report", style_heading),
            Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}", style_body),
            Spacer(1, 20)
        ]

        header = [[Paragraph(h, style_th) for h in
                   ["Risk Level", "Orders", "Revenue ($)", "Profit ($)", "Avg Delay (Days)", "% of Total"]]]
        row_colors = {"High": colors.HexColor("#FED7D7"), "Medium": colors.HexColor("#FEFCBF"), "Low": colors.HexColor("#C6F6D5")}

        table_data = header
        for row in risk_data:
            table_data.append([
                Paragraph(row["Risk_Level"], style_td),
                Paragraph(str(row["Count"]), style_td),
                Paragraph(f"${row['Total_Revenue']:,.2f}", style_td),
                Paragraph(f"${row['Total_Profit']:,.2f}", style_td),
                Paragraph(str(row["Avg_Delay"]), style_td),
                Paragraph(f"{row['Percentage']}%", style_td),
            ])

        t = Table(table_data, colWidths=[80, 60, 90, 80, 90, 64])
        row_style_cmds = [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                          ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                          ('PADDING', (0, 0), (-1, -1), 6), ('ALIGN', (0, 0), (-1, -1), 'LEFT')]
        for i, row in enumerate(risk_data, start=1):
            bg = row_colors.get(row["Risk_Level"], colors.white)
            row_style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
        t.setStyle(TableStyle(row_style_cmds))
        story.append(t)

        doc.build(story)
        return output_path

    @staticmethod
    def generate_supplier_performance_excel(output_path):
        """Generates a detailed Supplier Performance Excel report."""
        supplier_df = pd.DataFrame(execute_query("""
            SELECT
                s.Supplier_Name, s.Supplier_Rating AS Rating, s.Supplier_Status AS Status,
                COUNT(f.Fact_ID) AS Total_Orders,
                ROUND(SUM(f.Sales), 2) AS Total_Sales,
                ROUND(SUM(f.Profit), 2) AS Total_Profit,
                ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay_Days,
                SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS Delayed_Orders,
                SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS High_Risk,
                SUM(CASE WHEN f.Risk_Level = 'Low' THEN 1 ELSE 0 END) AS Low_Risk
            FROM dim_supplier s
            LEFT JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
            GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating, s.Supplier_Status
            ORDER BY Rating DESC
        """))

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            supplier_df.to_excel(writer, sheet_name="Supplier Performance", index=False)
        return output_path

    @staticmethod
    def generate_monthly_report_excel(output_path, year=None, month=None):
        """Generates a monthly performance Excel report filtered by year/month."""
        conditions = []
        if year:
            conditions.append(f"d.Year = {int(year)}")
        if month:
            conditions.append(f"d.Month = {int(month)}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        monthly_df = pd.DataFrame(execute_query(f"""
            SELECT
                d.Year, d.Month, d.Month_Name,
                COUNT(DISTINCT f.Order_ID) AS Total_Orders,
                SUM(f.Quantity) AS Units_Sold,
                ROUND(SUM(f.Sales), 2) AS Monthly_Revenue,
                ROUND(SUM(f.Profit), 2) AS Monthly_Profit,
                ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay,
                SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS High_Risk
            FROM fact_order f
            JOIN dim_date d ON f.Date_ID = d.Date_ID
            {where}
            GROUP BY d.Year, d.Month, d.Month_Name
            ORDER BY d.Year ASC, d.Month ASC
        """))

        risk_df = pd.DataFrame(execute_query(f"""
            SELECT f.Risk_Level, COUNT(*) AS Count, ROUND(SUM(f.Sales), 2) AS Revenue
            FROM fact_order f
            JOIN dim_date d ON f.Date_ID = d.Date_ID
            {where}
            GROUP BY f.Risk_Level
        """))

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            monthly_df.to_excel(writer, sheet_name="Monthly Performance", index=False)
            risk_df.to_excel(writer, sheet_name="Risk Distribution", index=False)
        return output_path

    @staticmethod
    def generate_yearly_report_excel(output_path, year=None):
        """Generates a yearly summary Excel report."""
        year_filter = f"WHERE d.Year = {int(year)}" if year else ""

        yearly_df = pd.DataFrame(execute_query(f"""
            SELECT
                d.Year,
                COUNT(DISTINCT f.Order_ID) AS Total_Orders,
                ROUND(SUM(f.Sales), 2) AS Annual_Revenue,
                ROUND(SUM(f.Profit), 2) AS Annual_Profit,
                ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay,
                SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS High_Risk,
                SUM(CASE WHEN f.Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS Med_Risk,
                SUM(CASE WHEN f.Risk_Level = 'Low' THEN 1 ELSE 0 END) AS Low_Risk
            FROM fact_order f
            JOIN dim_date d ON f.Date_ID = d.Date_ID
            {year_filter}
            GROUP BY d.Year
            ORDER BY d.Year ASC
        """))

        top_products_df = pd.DataFrame(execute_query(f"""
            SELECT p.Product_Name, SUM(f.Quantity) AS Units_Sold,
                   ROUND(SUM(f.Sales), 2) AS Revenue
            FROM fact_order f
            JOIN dim_product p ON f.Product_ID = p.Product_ID
            JOIN dim_date d ON f.Date_ID = d.Date_ID
            {year_filter}
            GROUP BY p.Product_ID, p.Product_Name
            ORDER BY Revenue DESC LIMIT 20
        """))

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            yearly_df.to_excel(writer, sheet_name="Yearly Summary", index=False)
            top_products_df.to_excel(writer, sheet_name="Top Products", index=False)
        return output_path
