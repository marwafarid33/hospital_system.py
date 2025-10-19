import streamlit as st
import sqlite3
from sqlite3 import Connection
import pandas as pd
import datetime

DB_PATH = "hospital.db"

# ---------- Database helpers ----------

def get_conn() -> Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    # doctors
    c.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY,
            name TEXT,
            specialty TEXT,
            phone TEXT,
            notes TEXT
        )
    ''')
    # patients
    c.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY,
            name TEXT,
            dob TEXT,
            gender TEXT,
            phone TEXT,
            address TEXT,
            notes TEXT
        )
    ''')
    # appointments
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY,
            patient_id INTEGER,
            doctor_id INTEGER,
            date TEXT,
            time TEXT,
            status TEXT,
            reason TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        )
    ''')
    # inventory
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            quantity INTEGER,
            unit_price REAL,
            notes TEXT
        )
    ''')
    # bills
    c.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY,
            patient_id INTEGER,
            date TEXT,
            total REAL,
            paid REAL,
            status TEXT,
            details TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    ''')
    conn.commit()
    conn.close()


# ---------- CRUD helpers ----------

def run_query(query, params=(), fetch=False):
    conn = get_conn()
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    conn.commit()
    conn.close()


# Patients
def add_patient(name, dob, gender, phone, address, notes):
    run_query("INSERT INTO patients (name,dob,gender,phone,address,notes) VALUES (?,?,?,?,?,?)",
              (name, dob, gender, phone, address, notes))


def update_patient(pid, name, dob, gender, phone, address, notes):
    run_query("UPDATE patients SET name=?,dob=?,gender=?,phone=?,address=?,notes=? WHERE id=?",
              (name, dob, gender, phone, address, notes, pid))


def delete_patient(pid):
    run_query("DELETE FROM patients WHERE id=?", (pid,))


def get_patients(filter_text=""):
    if filter_text:
        q = "%" + filter_text + "%"
        return run_query("SELECT * FROM patients WHERE name LIKE ? OR phone LIKE ?", (q, q), fetch=True)
    return run_query("SELECT * FROM patients", fetch=True)


# Doctors
def add_doctor(name, specialty, phone, notes):
    run_query("INSERT INTO doctors (name,specialty,phone,notes) VALUES (?,?,?,?)", (name, specialty, phone, notes))


def update_doctor(did, name, specialty, phone, notes):
    run_query("UPDATE doctors SET name=?,specialty=?,phone=?,notes=? WHERE id=?", (name, specialty, phone, notes, did))


def delete_doctor(did):
    run_query("DELETE FROM doctors WHERE id=?", (did,))


def get_doctors(filter_text=""):
    if filter_text:
        q = "%" + filter_text + "%"
        return run_query("SELECT * FROM doctors WHERE name LIKE ? OR specialty LIKE ?", (q, q), fetch=True)
    return run_query("SELECT * FROM doctors", fetch=True)


# Appointments

def add_appointment(patient_id, doctor_id, date, time, reason):
    run_query("INSERT INTO appointments (patient_id,doctor_id,date,time,status,reason) VALUES (?,?,?,?,?,?)",
              (patient_id, doctor_id, date, time, 'Scheduled', reason))


def update_appointment(aid, date, time, status, reason):
    run_query("UPDATE appointments SET date=?,time=?,status=?,reason=? WHERE id=?", (date, time, status, reason, aid))


def get_appointments(date_from=None, date_to=None, status=None):
    q = "SELECT a.*, p.name as patient_name, d.name as doctor_name FROM appointments a LEFT JOIN patients p ON a.patient_id=p.id LEFT JOIN doctors d ON a.doctor_id=d.id"
    conditions = []
    params = []
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if conditions:
        q += " WHERE " + " AND ".join(conditions)
    q += " ORDER BY date, time"
    return run_query(q, tuple(params), fetch=True)


# Inventory

def add_inventory(name, category, quantity, unit_price, notes):
    run_query("INSERT INTO inventory (name,category,quantity,unit_price,notes) VALUES (?,?,?,?,?)", (name, category, quantity, unit_price, notes))


def update_inventory(iid, name, category, quantity, unit_price, notes):
    run_query("UPDATE inventory SET name=?,category=?,quantity=?,unit_price=?,notes=? WHERE id=?", (name, category, quantity, unit_price, notes, iid))


def get_inventory(filter_text=""):
    if filter_text:
        q = "%" + filter_text + "%"
        return run_query("SELECT * FROM inventory WHERE name LIKE ? OR category LIKE ?", (q, q), fetch=True)
    return run_query("SELECT * FROM inventory", fetch=True)


# Billing

def add_bill(patient_id, total, paid, details):
    status = 'Paid' if paid >= total else 'Unpaid'
    run_query("INSERT INTO bills (patient_id,date,total,paid,status,details) VALUES (?,?,?,?,?,?)",
              (patient_id, datetime.date.today().isoformat(), total, paid, status, details))


def update_bill(bid, paid):
    row = run_query("SELECT * FROM bills WHERE id=?", (bid,), fetch=True)
    if not row:
        return
    total = row[0]['total']
    new_paid = row[0]['paid'] + paid
    status = 'Paid' if new_paid >= total else 'Unpaid'
    run_query("UPDATE bills SET paid=?,status=? WHERE id=?", (new_paid, status, bid))


def get_bills(patient_id=None, status=None):
    q = "SELECT b.*, p.name as patient_name FROM bills b LEFT JOIN patients p ON b.patient_id=p.id"
    conditions = []
    params = []
    if patient_id:
        conditions.append("patient_id=?")
        params.append(patient_id)
    if status:
        conditions.append("status=?")
        params.append(status)
    if conditions:
        q += " WHERE " + " AND ".join(conditions)
    q += " ORDER BY date DESC"
    return run_query(q, tuple(params), fetch=True)


# ---------- UI ----------

st.set_page_config(page_title="Hospital System", layout="wide")
init_db()

# Sidebar & Navigation (no authentication)
with st.sidebar:
    st.title("نظام إدارة المستشفى")
    st.markdown("---")
    st.markdown("### تنقل")
    menu = st.radio("", [
        "Dashboard",
        "Patients",
        "Doctors",
        "Appointments",
        "Inventory",
        "Billing",
        "Reports",
        "Settings",
    ])

# Dashboard
if menu == 'Dashboard':
    st.header("لوحة التحكم")
    col1, col2, col3 = st.columns(3)
    today = datetime.date.today().isoformat()
    appts_today = get_appointments(date_from=today, date_to=today)
    bills_unpaid = get_bills(status='Unpaid')
    low_stock = [i for i in get_inventory() if i['quantity'] <= 5]
    col1.metric("مواعيد اليوم", len(appts_today))
    col2.metric("فواتير غير مدفوعة", len(bills_unpaid))
    col3.metric("أصناف منخفضة المخزون", len(low_stock))

    st.subheader("المواعيد القادمة")
    st.dataframe(pd.DataFrame(get_appointments(date_from=today)))

# Patients
elif menu == 'Patients':
    st.header("إدارة المرضى")
    with st.expander("إضافة مريض جديد"):
        name = st.text_input("الاسم", key='p_name')
        dob = st.date_input("تاريخ الميلاد", key='p_dob')
        gender = st.selectbox("النوع", ["ذكر", "أنثى", "آخر"], key='p_gender')
        phone = st.text_input("الهاتف", key='p_phone')
        address = st.text_area("العنوان", key='p_address')
        notes = st.text_area("ملاحظات", key='p_notes')
        if st.button("إضافة مريض"):
            add_patient(name, dob.isoformat(), gender, phone, address, notes)
            st.success("تمت إضافة المريض")

    st.subheader("قائمة المرضى")
    f = st.text_input("بحث باسم أو هاتف")
    patients = get_patients(f)
    df = pd.DataFrame(patients)
    st.dataframe(df)

    if not df.empty:
        sel = st.selectbox("اختر مريض للتعديل/حذف", df['id'].astype(str) + ' - ' + df['name'])
        pid = int(sel.split(' - ')[0])
        p = [x for x in patients if x['id'] == pid][0]
        st.write(f"**{p['name']}**")
        name = st.text_input("الاسم", p['name'], key='edit_p_name')
        dob = st.date_input("تاريخ الميلاد", datetime.date.fromisoformat(p['dob']) if p['dob'] else datetime.date.today(), key='edit_p_dob')
        gender = st.selectbox("النوع", ["ذكر", "أنثى", "آخر"], index=0 if p['gender']=='ذكر' else 1 if p['gender']=='أنثى' else 2, key='edit_p_gender')
        phone = st.text_input("الهاتف", p['phone'], key='edit_p_phone')
        address = st.text_area("العنوان", p['address'], key='edit_p_address')
        notes = st.text_area("ملاحظات", p['notes'], key='edit_p_notes')
        col1, col2 = st.columns(2)
        if col1.button("حفظ التعديلات"):
            update_patient(pid, name, dob.isoformat(), gender, phone, address, notes)
            st.success("تم الحفظ")
        if col2.button("حذف المريض"):
            delete_patient(pid)
            st.success("تم الحذف")

# Doctors
elif menu == 'Doctors':
    st.header("إدارة الأطباء")
    with st.expander("إضافة طبيب جديد"):
        name = st.text_input("الاسم", key='d_name')
        specialty = st.text_input("التخصص", key='d_specialty')
        phone = st.text_input("الهاتف", key='d_phone')
        notes = st.text_area("ملاحظات", key='d_notes')
        if st.button("إضافة طبيب"):
            add_doctor(name, specialty, phone, notes)
            st.success("تمت إضافة الطبيب")

    st.subheader("قائمة الأطباء")
    f = st.text_input("بحث باسم أو تخصص")
    doctors = get_doctors(f)
    df = pd.DataFrame(doctors)
    st.dataframe(df)

    if not df.empty:
        sel = st.selectbox("اختر طبيب للتعديل/حذف", df['id'].astype(str) + ' - ' + df['name'])
        did = int(sel.split(' - ')[0])
        d = [x for x in doctors if x['id'] == did][0]
        st.write(f"**{d['name']}**")
        name = st.text_input("الاسم", d['name'], key='edit_d_name')
        specialty = st.text_input("التخصص", d['specialty'], key='edit_d_specialty')
        phone = st.text_input("الهاتف", d['phone'], key='edit_d_phone')
        notes = st.text_area("ملاحظات", d['notes'], key='edit_d_notes')
        col1, col2 = st.columns(2)
        if col1.button("حفظ التعديلات"):
            update_doctor(did, name, specialty, phone, notes)
            st.success("تم الحفظ")
        if col2.button("حذف الطبيب"):
            delete_doctor(did)
            st.success("تم الحذف")

# Appointments
elif menu == 'Appointments':
    st.header("المواعيد")
    st.subheader("حجز موعد")
    patients = get_patients()
    doctors = get_doctors()
    if patients and doctors:
        p_map = {f"{p['id']} - {p['name']}": p['id'] for p in patients}
        d_map = {f"{d['id']} - {d['name']}": d['id'] for d in doctors}
        p_sel = st.selectbox("المريض", list(p_map.keys()))
        d_sel = st.selectbox("الطبيب", list(d_map.keys()))
        date = st.date_input("تاريخ")
        time = st.time_input("الوقت")
        reason = st.text_area("السبب")
        if st.button("حجز"):
            add_appointment(p_map[p_sel], d_map[d_sel], date.isoformat(), time.strftime('%H:%M'), reason)
            st.success("تم حجز الموعد")
    else:
        st.info("أضف أطباء ومرضى أولاً")

    st.markdown("---")
    st.subheader("قائمة المواعيد")
    date_from = st.date_input("من تاريخ", value=datetime.date.today())
    date_to = st.date_input("إلى تاريخ", value=datetime.date.today() + datetime.timedelta(days=7))
    status = st.selectbox("الحالة", ['All', 'Scheduled', 'Completed', 'Cancelled'])
    status_filter = None if status == 'All' else status
    appts = get_appointments(date_from=date_from.isoformat(), date_to=date_to.isoformat(), status=status_filter)
    if appts:
        df = pd.DataFrame(appts)
        st.dataframe(df)
        sel = st.selectbox("اختر موعد لتعديله", df['id'].astype(str) + ' - ' + df['patient_name'])
        aid = int(sel.split(' - ')[0])
        a = [x for x in appts if x['id'] == aid][0]
        date = st.date_input("تاريخ", datetime.date.fromisoformat(a['date']))
        time = st.time_input("الوقت", datetime.datetime.strptime(a['time'], '%H:%M').time())
        status = st.selectbox("الحالة", ['Scheduled', 'Completed', 'Cancelled'], index=0 if a['status']=='Scheduled' else 1 if a['status']=='Completed' else 2)
        reason = st.text_area("السبب", a['reason'])
        if st.button("حفظ التعديل"):
            update_appointment(aid, date.isoformat(), time.strftime('%H:%M'), status, reason)
            st.success("تم الحفظ")

# Inventory
elif menu == 'Inventory':
    st.header("المخزون")
    with st.expander("إضافة صنف"):
        name = st.text_input("الاسم", key='i_name')
        category = st.text_input("الفئة", key='i_cat')
        quantity = st.number_input("الكمية", min_value=0, value=1, step=1, key='i_qty')
        unit_price = st.number_input("سعر الوحدة", min_value=0.0, value=0.0, step=0.1, key='i_price')
        notes = st.text_area("ملاحظات", key='i_notes')
        if st.button("إضافة للصنف"):
            add_inventory(name, category, quantity, unit_price, notes)
            st.success("تمت الإضافة")

    f = st.text_input("بحث في المخزون")
    items = get_inventory(f)
    df = pd.DataFrame(items)
    st.dataframe(df)

    if not df.empty:
        sel = st.selectbox("اختر صنف للتعديل", df['id'].astype(str) + ' - ' + df['name'])
        iid = int(sel.split(' - ')[0])
        it = [x for x in items if x['id'] == iid][0]
        name = st.text_input("الاسم", it['name'], key='edit_i_name')
        category = st.text_input("الفئة", it['category'], key='edit_i_cat')
        quantity = st.number_input("الكمية", min_value=0, value=int(it['quantity']), key='edit_i_qty')
        unit_price = st.number_input("سعر الوحدة", min_value=0.0, value=float(it['unit_price'] or 0.0), key='edit_i_price')
        notes = st.text_area("ملاحظات", it['notes'], key='edit_i_notes')
        if st.button("حفظ الصنف"):
            update_inventory(iid, name, category, quantity, unit_price, notes)
            st.success("تم الحفظ")

# Billing
elif menu == 'Billing':
    st.header("الفواتير")
    patients = get_patients()
    if patients:
        p_map = {f"{p['id']} - {p['name']}": p['id'] for p in patients}
        sel = st.selectbox("المريض", list(p_map.keys()))
        pid = p_map[sel]
        total = st.number_input("المجموع", min_value=0.0, value=0.0)
        paid = st.number_input("المدفوع", min_value=0.0, value=0.0)
        details = st.text_area("تفاصيل الفاتورة")
        if st.button("إضافة فاتورة"):
            add_bill(pid, total, paid, details)
            st.success("تمت إضافة الفاتورة")

    st.markdown("---")
    st.subheader("قائمة الفواتير")
    bstatus = st.selectbox("الحالة", ['All', 'Paid', 'Unpaid'])
    status_filter = None if bstatus == 'All' else bstatus
    bills = get_bills(status=status_filter)
    df = pd.DataFrame(bills)
    st.dataframe(df)
    if not df.empty:
        sel = st.selectbox("اختر فاتورة لتسجيل دفعة", df['id'].astype(str) + ' - ' + df['patient_name'])
        bid = int(sel.split(' - ')[0])
        amount = st.number_input("قيمة الدفع", min_value=0.0, value=0.0)
        if st.button("تسجيل دفعة"):
            update_bill(bid, amount)
            st.success("تم تسجيل الدفع")

# Reports
elif menu == 'Reports':
    st.header("تقارير")
    st.subheader("تقرير المواعيد لفترة")
    df_appts = pd.DataFrame(get_appointments())
    if not df_appts.empty:
        st.write("تنزيل تقرير المواعيد كـ CSV")
        csv = df_appts.to_csv(index=False).encode('utf-8')
        st.download_button("تحميل CSV", data=csv, file_name='appointments_report.csv', mime='text/csv')

    st.subheader("فواتير غير مدفوعة")
    unpaid = pd.DataFrame(get_bills(status='Unpaid'))
    st.dataframe(unpaid)
    if not unpaid.empty:
        st.download_button("تحميل الفواتير غير المدفوعة", data=unpaid.to_csv(index=False).encode('utf-8'), file_name='unpaid_bills.csv')

# Settings
elif menu == 'Settings':
    st.header("الإعدادات")
    st.markdown("هذه الصفحة مخصصة لإعدادات عامة. بما أن النظام الآن بدون تسجيل دخول، لا توجد إدارة مستخدمين.")

# Footer
st.markdown("---")
st.caption("نظام مستشفى مبسط — مبني ببايثون و Streamlit. للتخصيص أو إضافة ميزات متقدمة، أخبرني بما تريد بالضبط.")
