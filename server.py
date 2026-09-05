"""GreenPaws beginner-friendly local backend. Run: python server.py"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import sqlite3, json, os, mimetypes
from datetime import datetime
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "greenpaws.db")
SEED = [
 ("Pawfect Adult Dog Food","Pet Food",1450,24,"Pawfect","3 kg","🐶","Best seller","Balanced chicken and rice nutrition for energetic adult dogs."),
 ("Whisker Care Cat Food","Pet Food",980,18,"Whisker Care","1.2 kg","🐱","New","Complete ocean-fish recipe made for healthy, happy cats."),
 ("Organic Tomato Seeds","Plant Seeds",120,42,"GreenPaws Grow","20 seeds","🍅","Popular","Sweet, productive tomatoes for sunny balconies and gardens."),
 ("Kitchen Herb Garden Kit","Plant Seeds",350,8,"GreenPaws Grow","5 varieties","🌿","New","An easy kitchen herb collection."),
 ("Sunflower Seed Pack","Plant Seeds",150,31,"GreenPaws Grow","15 seeds","🌻","","Cheerful giant sunflowers."),
 ("Natural Pet Treats","Accessories",420,13,"Pawfect","250 g","🦴","","Wholesome crunchy treats."),
]
def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def rows(cursor): return [dict(x) for x in cursor.fetchall()]
def setup():
    c=conn(); c.executescript('''
    CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT, price REAL NOT NULL, stock INTEGER NOT NULL DEFAULT 0, brand TEXT, weight TEXT, emoji TEXT, tag TEXT, description TEXT, active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, email TEXT, address TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(phone), UNIQUE(email));
    CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY, order_no TEXT UNIQUE, customer_id INTEGER NOT NULL, payment TEXT, status TEXT DEFAULT 'Pending', total REAL NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(customer_id) REFERENCES customers(id));
    CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, product_name TEXT, quantity INTEGER, unit_price REAL, FOREIGN KEY(order_id) REFERENCES orders(id));
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, event TEXT, detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    ''')
    if not c.execute("SELECT id FROM products LIMIT 1").fetchone(): c.executemany("INSERT INTO products(name,category,price,stock,brand,weight,emoji,tag,description) VALUES(?,?,?,?,?,?,?,?,?)", SEED)
    c.commit(); c.close()
class API(SimpleHTTPRequestHandler):
    def log_message(self,*args): print("[GreenPaws]",*args)
    def send_json(self,data,status=200):
        out=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(out))); self.end_headers(); self.wfile.write(out)
    def body(self):
        try:return json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))) or b'{}')
        except json.JSONDecodeError:return {}
    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path
        if not path.startswith('/api/'): return super().do_GET()
        c=conn()
        if path=='/api/products': data=rows(c.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC"))
        elif path=='/api/admin/products': data=rows(c.execute("SELECT * FROM products ORDER BY id DESC"))
        elif path=='/api/orders': data=rows(c.execute("SELECT o.*,c.name,c.phone,c.email,c.address FROM orders o JOIN customers c ON c.id=o.customer_id ORDER BY o.id DESC"))
        elif path=='/api/track':
            q=parse_qs(parsed.query); order_no=q.get('order_no',[''])[0].upper(); contact=q.get('contact',[''])[0]; found=c.execute("SELECT o.order_no,o.status,o.created_at FROM orders o JOIN customers c ON c.id=o.customer_id WHERE o.order_no=? AND (c.phone=? OR c.email=?)",(order_no,contact,contact)).fetchone(); data=dict(found) if found else None
        elif path=='/api/customers': data=rows(c.execute("SELECT c.*,COUNT(o.id) order_count,COALESCE(SUM(o.total),0) total_spending FROM customers c LEFT JOIN orders o ON o.customer_id=c.id GROUP BY c.id ORDER BY c.id DESC"))
        elif path.startswith('/api/customers/'):
            cid=path.rsplit('/',1)[1]; customer=c.execute("SELECT * FROM customers WHERE id=?",(cid,)).fetchone(); data={"customer":dict(customer) if customer else None,"orders":rows(c.execute("SELECT * FROM orders WHERE customer_id=? ORDER BY id DESC",(cid,)))}
        elif path=='/api/dashboard':
            revenue=c.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status!='Cancelled'").fetchone()[0]; data={"revenue":revenue,"orders":c.execute("SELECT COUNT(*) FROM orders").fetchone()[0],"customers":c.execute("SELECT COUNT(*) FROM customers").fetchone()[0],"low_stock":c.execute("SELECT COUNT(*) FROM products WHERE stock<10 AND active=1").fetchone()[0],"events":rows(c.execute("SELECT event,COUNT(*) count FROM events GROUP BY event ORDER BY count DESC LIMIT 6")),"low_products":rows(c.execute("SELECT * FROM products WHERE stock<10 AND active=1"))}
        else: c.close(); return self.send_json({"error":"Not found"},404)
        c.close(); self.send_json(data)
    def do_POST(self):
        path=urlparse(self.path).path; d=self.body(); c=conn()
        if path=='/api/products':
            c.execute("INSERT INTO products(name,category,price,stock,brand,weight,emoji,tag,description) VALUES(?,?,?,?,?,?,?,?,?)",(d.get('name'),d.get('category','Pet Food'),d.get('price',0),d.get('stock',0),d.get('brand',''),d.get('weight',''),d.get('emoji','📦'),d.get('tag',''),d.get('description',''))); c.commit(); data={"ok":True,"id":c.execute("SELECT last_insert_rowid()").fetchone()[0]}
        elif path=='/api/orders':
            required=['name','phone','address','items'];
            if any(not d.get(k) for k in required): c.close(); return self.send_json({"error":"Name, phone, address and cart items are required."},400)
            existing=c.execute("SELECT id FROM customers WHERE phone=? OR (email=? AND email!='')",(d['phone'],d.get('email',''))).fetchone()
            if existing: cid=existing['id']; c.execute("UPDATE customers SET name=?,email=?,address=? WHERE id=?",(d['name'],d.get('email',''),d['address'],cid))
            else: c.execute("INSERT INTO customers(name,phone,email,address) VALUES(?,?,?,?)",(d['name'],d['phone'],d.get('email',''),d['address'])); cid=c.execute("SELECT last_insert_rowid()").fetchone()[0]
            total=0; checked=[]
            for i in d['items']:
                p=c.execute("SELECT * FROM products WHERE id=? AND active=1",(i.get('id'),)).fetchone(); q=max(1,int(i.get('qty',1)))
                if not p or p['stock']<q: c.close(); return self.send_json({"error":"A product is unavailable or does not have enough stock."},400)
                checked.append((p,q)); total+=p['price']*q
            if total<1500: total+=80
            c.execute("INSERT INTO orders(order_no,customer_id,payment,total) VALUES(?,?,?,?)",('TEMP',cid,d.get('payment','Cash on Delivery'),total)); oid=c.execute("SELECT last_insert_rowid()").fetchone()[0]; order_no=f'GP-{10000+oid}'; c.execute("UPDATE orders SET order_no=? WHERE id=?",(order_no,oid))
            for p,q in checked: c.execute("INSERT INTO order_items(order_id,product_id,product_name,quantity,unit_price) VALUES(?,?,?,?,?)",(oid,p['id'],p['name'],q,p['price'])); c.execute("UPDATE products SET stock=stock-? WHERE id=?",(q,p['id']))
            c.commit(); data={"ok":True,"order_no":order_no,"total":total}
        elif path=='/api/events': c.execute("INSERT INTO events(event,detail) VALUES(?,?)",(d.get('event','unknown'),json.dumps(d.get('detail',{})))); c.commit(); data={"ok":True}
        else: c.close(); return self.send_json({"error":"Not found"},404)
        c.close(); self.send_json(data,201)
    def do_PUT(self):
        path=urlparse(self.path).path; d=self.body(); c=conn()
        if path.startswith('/api/orders/'):
            c.execute("UPDATE orders SET status=? WHERE id=?",(d.get('status','Pending'),path.rsplit('/',1)[1]))
        elif path.startswith('/api/products/'):
            pid=path.rsplit('/',1)[1]; c.execute("UPDATE products SET name=?,category=?,price=?,stock=?,brand=?,weight=?,emoji=?,tag=?,description=?,active=? WHERE id=?",(d.get('name'),d.get('category'),d.get('price'),d.get('stock'),d.get('brand',''),d.get('weight',''),d.get('emoji','📦'),d.get('tag',''),d.get('description',''),d.get('active',1),pid))
        else: c.close(); return self.send_json({"error":"Not found"},404)
        c.commit(); c.close(); self.send_json({"ok":True})
def run():
    os.chdir(ROOT); setup(); print('GreenPaws backend running at http://localhost:8000'); ThreadingHTTPServer(('0.0.0.0',8000),API).serve_forever()
if __name__=='__main__': run()
