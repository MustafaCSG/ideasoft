import sqlite3
from flask import Flask, jsonify, request, render_template
from datetime import datetime

app = Flask(__name__)
DB_FILE = "ideahunter.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/leads', methods=['GET'])
def get_leads():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Select leads with design status joined from checked_domains
        query = """
        SELECT 
            l.domain, l.company_name, l.authorized_person, l.phone, l.email, l.address, 
            l.scraped_at, l.url, l.call_status, l.notes, l.tags, c.status AS design_status
        FROM scraped_leads l
        LEFT JOIN checked_domains c ON l.domain = c.domain
        ORDER BY l.scraped_at DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        leads = []
        for row in rows:
            leads.append({
                "domain": row["domain"],
                "company_name": row["company_name"] or "Bilinmiyor",
                "authorized_person": row["authorized_person"] or "",
                "phone": row["phone"] or "",
                "email": row["email"] or "",
                "address": row["address"] or "",
                "scraped_at": row["scraped_at"],
                "url": row["url"] or "",
                "call_status": row["call_status"] or "YENI",
                "notes": row["notes"] or "",
                "tags": row["tags"] or "",
                "design_status": row["design_status"] or "Bilinmiyor"
            })
            
        return jsonify(leads)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/leads/<domain>', methods=['PUT'])
def update_lead(domain):
    try:
        data = request.json or {}
        call_status = data.get("call_status")
        notes = data.get("notes")
        authorized_person = data.get("authorized_person")
        company_name = data.get("company_name")
        tags = data.get("tags")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify lead exists
        cursor.execute("SELECT 1 FROM scraped_leads WHERE domain = ?", (domain,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Lead not found"}), 404
            
        # Update columns dynamically based on what was passed
        fields = []
        params = []
        if call_status is not None:
            fields.append("call_status = ?")
            params.append(call_status)
        if notes is not None:
            fields.append("notes = ?")
            params.append(notes)
        if authorized_person is not None:
            fields.append("authorized_person = ?")
            params.append(authorized_person)
        if company_name is not None:
            fields.append("company_name = ?")
            params.append(company_name)
        if tags is not None:
            fields.append("tags = ?")
            params.append(tags)
            
        if not fields:
            conn.close()
            return jsonify({"error": "No fields to update"}), 400
            
        fields.append("updated_at = ?")
        params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        params.append(domain)
        sql_query = f"UPDATE scraped_leads SET {', '.join(fields)} WHERE domain = ?"
        
        cursor.execute(sql_query, params)
        conn.commit()
        conn.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Total Leads
        cursor.execute("SELECT COUNT(*) FROM scraped_leads")
        total_leads = cursor.fetchone()[0]
        
        # 2. Total Called (Not YENI)
        cursor.execute("SELECT COUNT(*) FROM scraped_leads WHERE call_status != 'YENI'")
        total_called = cursor.fetchone()[0]
        
        # 3. Status breakdown
        cursor.execute("SELECT call_status, COUNT(*) FROM scraped_leads GROUP BY call_status")
        status_rows = cursor.fetchall()
        status_breakdown = {row[0]: row[1] for row in status_rows}
        
        # 4. Design status breakdown
        cursor.execute("""
            SELECT c.status, COUNT(*) 
            FROM scraped_leads l
            LEFT JOIN checked_domains c ON l.domain = c.domain
            GROUP BY c.status
        """)
        design_rows = cursor.fetchall()
        design_breakdown = {row[0]: row[1] for row in design_rows}
        
        conn.close()
        
        # Fill default statuses if missing
        for s in ['YENI', 'ARANACAK', 'ULASILAMADI', 'TEKLIF_BEKLIYOR', 'OLUMLU', 'OLUMSUZ']:
            if s not in status_breakdown:
                status_breakdown[s] = 0
                
        return jsonify({
            "total_leads": total_leads,
            "total_called": total_called,
            "status_breakdown": status_breakdown,
            "design_breakdown": design_breakdown
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
