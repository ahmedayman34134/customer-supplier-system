from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
database_url = os.environ.get('DATABASE_URL', 'sqlite:///customer_supplier.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure logging
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

db = SQLAlchemy(app)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يرجى تسجيل الدخول للوصول إلى هذه الصفحة.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    email = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sales_invoices = db.relationship('SalesInvoice', backref='customer', lazy=True)
    collections = db.relationship('Collection', backref='customer', lazy=True)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    email = db.Column(db.String(100))
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchase_invoices = db.relationship('PurchaseInvoice', backref='supplier', lazy=True)
    payments = db.relationship('Payment', backref='supplier', lazy=True)

class SalesInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    invoice_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class PurchaseInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    invoice_date = db.Column(db.Date, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    collection_date = db.Column(db.Date, default=date.today)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

# Routes
@app.route('/')
@login_required
def dashboard():
    # Get summary statistics
    total_customers = Customer.query.count()
    total_suppliers = Supplier.query.count()
    total_sales_invoices = SalesInvoice.query.count()
    total_purchase_invoices = PurchaseInvoice.query.count()
    
    # Get recent activities
    recent_sales = SalesInvoice.query.order_by(SalesInvoice.created_at.desc()).limit(5).all()
    recent_purchases = PurchaseInvoice.query.order_by(PurchaseInvoice.created_at.desc()).limit(5).all()
    
    # Calculate balances
    total_customer_balance = sum(customer.balance for customer in Customer.query.all())
    total_supplier_balance = sum(supplier.balance for supplier in Supplier.query.all())
    
    return render_template('dashboard.html', 
                         total_customers=total_customers,
                         total_suppliers=total_suppliers,
                         total_sales_invoices=total_sales_invoices,
                         total_purchase_invoices=total_purchase_invoices,
                         total_customer_balance=total_customer_balance,
                         total_supplier_balance=total_supplier_balance,
                         recent_sales=recent_sales,
                         recent_purchases=recent_purchases)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Customer routes
@app.route('/customers')
@login_required
def customers():
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            email=request.form.get('email')
        )
        db.session.add(customer)
        db.session.commit()
        flash('تم إضافة العميل بنجاح', 'success')
        return redirect(url_for('customers'))
    
    return render_template('add_customer.html')

@app.route('/view_customer/<int:id>')
@login_required
def view_customer(id):
    customer = Customer.query.get_or_404(id)
    return render_template('view_customer.html', customer=customer)

@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')
        customer.email = request.form.get('email')
        
        db.session.commit()
        flash('تم تحديث بيانات العميل بنجاح', 'success')
        return redirect(url_for('customers'))
    
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete_customer/<int:id>', methods=['POST'])
@login_required
def delete_customer(id):
    try:
        customer = Customer.query.get_or_404(id)
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Supplier routes
@app.route('/suppliers')
@login_required
def suppliers():
    suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/add_supplier', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if request.method == 'POST':
        supplier = Supplier(
            name=request.form['name'],
            phone=request.form.get('phone'),
            address=request.form.get('address'),
            email=request.form.get('email')
        )
        db.session.add(supplier)
        db.session.commit()
        flash('تم إضافة المورد بنجاح', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('add_supplier.html')

@app.route('/view_supplier/<int:id>')
@login_required
def view_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    return render_template('view_supplier.html', supplier=supplier)

@app.route('/edit_supplier/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    
    if request.method == 'POST':
        supplier.name = request.form['name']
        supplier.phone = request.form.get('phone')
        supplier.address = request.form.get('address')
        supplier.email = request.form.get('email')
        
        db.session.commit()
        flash('تم تحديث بيانات المورد بنجاح', 'success')
        return redirect(url_for('suppliers'))
    
    return render_template('edit_supplier.html', supplier=supplier)

@app.route('/delete_supplier/<int:id>', methods=['POST'])
@login_required
def delete_supplier(id):
    try:
        supplier = Supplier.query.get_or_404(id)
        db.session.delete(supplier)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Sales Invoice routes
@app.route('/sales_invoices')
@login_required
def sales_invoices():
    invoices = SalesInvoice.query.order_by(SalesInvoice.created_at.desc()).all()
    return render_template('sales_invoices.html', invoices=invoices)

@app.route('/add_sales_invoice', methods=['GET', 'POST'])
@login_required
def add_sales_invoice():
    if request.method == 'POST':
        invoice = SalesInvoice(
            invoice_number=request.form['invoice_number'],
            customer_id=request.form['customer_id'],
            amount=float(request.form['amount']),
            description=request.form.get('description'),
            invoice_date=datetime.strptime(request.form['invoice_date'], '%Y-%m-%d').date(),
            created_by=current_user.id
        )
        
        # Update customer balance
        customer = Customer.query.get(invoice.customer_id)
        customer.balance += invoice.amount
        
        db.session.add(invoice)
        db.session.commit()
        flash('تم إضافة فاتورة المبيعات بنجاح', 'success')
        return redirect(url_for('sales_invoices'))
    
    customers = Customer.query.all()
    return render_template('add_sales_invoice.html', customers=customers)


@app.route('/delete_sales_invoice/<int:id>', methods=['POST'])
@login_required
def delete_sales_invoice(id):
    try:
        invoice = SalesInvoice.query.get_or_404(id)
        customer = invoice.customer
        
        # Reverse customer balance
        customer.balance -= invoice.amount
        
        # Delete the invoice
        db.session.delete(invoice)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Purchase Invoice routes
@app.route('/purchase_invoices')
@login_required
def purchase_invoices():
    invoices = PurchaseInvoice.query.order_by(PurchaseInvoice.created_at.desc()).all()
    return render_template('purchase_invoices.html', invoices=invoices)

@app.route('/add_purchase_invoice', methods=['GET', 'POST'])
@login_required
def add_purchase_invoice():
    if request.method == 'POST':
        invoice = PurchaseInvoice(
            invoice_number=request.form['invoice_number'],
            supplier_id=request.form['supplier_id'],
            amount=float(request.form['amount']),
            description=request.form.get('description'),
            invoice_date=datetime.strptime(request.form['invoice_date'], '%Y-%m-%d').date(),
            created_by=current_user.id
        )
        
        # Update supplier balance
        supplier = Supplier.query.get(invoice.supplier_id)
        supplier.balance += invoice.amount
        
        db.session.add(invoice)
        db.session.commit()
        flash('تم إضافة فاتورة المشتريات بنجاح', 'success')
        return redirect(url_for('purchase_invoices'))
    
    suppliers = Supplier.query.all()
    return render_template('add_purchase_invoice.html', suppliers=suppliers)


@app.route('/delete_purchase_invoice/<int:id>', methods=['POST'])
@login_required
def delete_purchase_invoice(id):
    try:
        invoice = PurchaseInvoice.query.get_or_404(id)
        supplier = invoice.supplier
        
        # Reverse supplier balance
        supplier.balance -= invoice.amount
        
        # Delete the invoice
        db.session.delete(invoice)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Collection routes
@app.route('/collections')
@login_required
def collections():
    collections = Collection.query.order_by(Collection.created_at.desc()).all()
    return render_template('collections.html', collections=collections)

@app.route('/add_collection', methods=['GET', 'POST'])
@login_required
def add_collection():
    if request.method == 'POST':
        try:
            app.logger.debug(f"Form data: {request.form}")
            
            customer_id = request.form.get('customer_id')
            amount = request.form.get('amount')
            collection_date = request.form.get('collection_date')
            notes = request.form.get('notes', '')
            
            app.logger.debug(f"Customer ID: {customer_id}, Amount: {amount}, Date: {collection_date}")
            
            if not customer_id or not amount or not collection_date:
                flash('جميع الحقول المطلوبة يجب ملؤها', 'error')
                return redirect(url_for('add_collection'))
            
            collection = Collection(
                customer_id=int(customer_id),
                amount=float(amount),
                collection_date=datetime.strptime(collection_date, '%Y-%m-%d').date(),
                notes=notes,
                created_by=current_user.id
            )
            
            # Update customer balance
            customer = Customer.query.get(collection.customer_id)
            if customer:
                customer.balance -= collection.amount
                app.logger.debug(f"Updated customer {customer.name} balance to {customer.balance}")
            
            db.session.add(collection)
            db.session.commit()
            flash('تم إضافة التحصيل بنجاح', 'success')
            return redirect(url_for('collections'))
        except Exception as e:
            app.logger.error(f"Error adding collection: {str(e)}")
            db.session.rollback()
            flash(f'حدث خطأ في إضافة التحصيل: {str(e)}', 'error')
            return redirect(url_for('add_collection'))
    
    customers = Customer.query.all()
    return render_template('add_collection.html', customers=customers, today=date.today())


@app.route('/delete_collection/<int:id>', methods=['POST'])
@login_required
def delete_collection(id):
    try:
        collection = Collection.query.get_or_404(id)
        customer = collection.customer
        
        # Reverse customer balance
        customer.balance += collection.amount
        
        # Delete the collection
        db.session.delete(collection)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Payment routes
@app.route('/payments')
@login_required
def payments():
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template('payments.html', payments=payments)

@app.route('/add_payment', methods=['GET', 'POST'])
@login_required
def add_payment():
    if request.method == 'POST':
        try:
            app.logger.debug(f"Payment form data: {request.form}")
            
            supplier_id = request.form.get('supplier_id')
            amount = request.form.get('amount')
            payment_date = request.form.get('payment_date')
            notes = request.form.get('notes', '')
            
            app.logger.debug(f"Supplier ID: {supplier_id}, Amount: {amount}, Date: {payment_date}")
            
            if not supplier_id or not amount or not payment_date:
                flash('جميع الحقول المطلوبة يجب ملؤها', 'error')
                return redirect(url_for('add_payment'))
            
            payment = Payment(
                supplier_id=int(supplier_id),
                amount=float(amount),
                payment_date=datetime.strptime(payment_date, '%Y-%m-%d').date(),
                notes=notes,
                created_by=current_user.id
            )
            
            # Update supplier balance
            supplier = Supplier.query.get(payment.supplier_id)
            if supplier:
                supplier.balance -= payment.amount
                app.logger.debug(f"Updated supplier {supplier.name} balance to {supplier.balance}")
            
            db.session.add(payment)
            db.session.commit()
            flash('تم إضافة الدفع بنجاح', 'success')
            return redirect(url_for('payments'))
        except Exception as e:
            app.logger.error(f"Error adding payment: {str(e)}")
            db.session.rollback()
            flash(f'حدث خطأ في إضافة الدفع: {str(e)}', 'error')
            return redirect(url_for('add_payment'))
    
    suppliers = Supplier.query.all()
    return render_template('add_payment.html', suppliers=suppliers, today=date.today())



@app.route('/delete_payment/<int:id>', methods=['POST'])
@login_required
def delete_payment(id):
    try:
        payment = Payment.query.get_or_404(id)
        supplier = payment.supplier
        
        # Reverse supplier balance
        supplier.balance += payment.amount
        
        # Delete the payment
        db.session.delete(payment)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# Customer statement
@app.route('/customer_statement/<int:customer_id>')
@login_required
def customer_statement(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    
    # Get all sales invoices for this customer
    sales_invoices = SalesInvoice.query.filter_by(customer_id=customer_id).order_by(SalesInvoice.invoice_date.desc()).all()
    
    # Get all collections for this customer
    collections = Collection.query.filter_by(customer_id=customer_id).order_by(Collection.collection_date.desc()).all()
    
    return render_template('customer_statement.html', 
                         customer=customer, 
                         sales_invoices=sales_invoices, 
                         collections=collections)

# Supplier statement
@app.route('/supplier_statement/<int:supplier_id>')
@login_required
def supplier_statement(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Get all purchase invoices for this supplier
    purchase_invoices = PurchaseInvoice.query.filter_by(supplier_id=supplier_id).order_by(PurchaseInvoice.invoice_date.desc()).all()
    
    # Get all payments for this supplier
    payments = Payment.query.filter_by(supplier_id=supplier_id).order_by(Payment.payment_date.desc()).all()
    
    return render_template('supplier_statement.html', 
                         supplier=supplier, 
                         purchase_invoices=purchase_invoices, 
                         payments=payments)

# Customer Reports
@app.route('/customer_reports')
@login_required
def customer_reports():
    customers = Customer.query.all()
    customer_data = []
    
    for customer in customers:
        total_invoices = sum(invoice.amount for invoice in customer.sales_invoices)
        total_collections = sum(collection.amount for collection in customer.collections)
        customer_data.append({
            'customer': customer,
            'total_invoices': total_invoices,
            'total_collections': total_collections,
            'balance': customer.balance
        })
    
    return render_template('customer_reports.html', customer_data=customer_data)

# Supplier Reports
@app.route('/supplier_reports')
@login_required
def supplier_reports():
    suppliers = Supplier.query.all()
    supplier_data = []
    
    for supplier in suppliers:
        total_invoices = sum(invoice.amount for invoice in supplier.purchase_invoices)
        total_payments = sum(payment.amount for payment in supplier.payments)
        supplier_data.append({
            'supplier': supplier,
            'total_invoices': total_invoices,
            'total_payments': total_payments,
            'balance': supplier.balance
        })
    
    return render_template('supplier_reports.html', supplier_data=supplier_data)

# Export Customer Reports to Excel
@app.route('/export_customers_excel')
@login_required
def export_customers_excel():
    try:
        import pandas as pd
        from io import BytesIO
        
        customers = Customer.query.all()
        customer_data = []
        
        for customer in customers:
            total_invoices = sum(invoice.amount for invoice in customer.sales_invoices)
            total_collections = sum(collection.amount for collection in customer.collections)
            customer_data.append({
                'الرقم': customer.id,
                'اسم العميل': customer.name,
                'الهاتف': customer.phone or '-',
                'البريد الإلكتروني': customer.email or '-',
                'الرصيد': customer.balance,
                'إجمالي الفواتير': total_invoices,
                'إجمالي التحصيلات': total_collections,
                'تاريخ الإضافة': customer.created_at.strftime('%Y-%m-%d')
            })
        
        df = pd.DataFrame(customer_data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='تقارير العملاء', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'تقارير_العملاء_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    except ImportError:
        flash('مكتبة pandas غير مثبتة. يرجى تثبيتها لاستخدام تصدير Excel', 'error')
        return redirect(url_for('customer_reports'))
    except Exception as e:
        flash(f'حدث خطأ في تصدير Excel: {str(e)}', 'error')
        return redirect(url_for('customer_reports'))

# Export Customer Reports to PDF
@app.route('/export_customers_pdf')
@login_required
def export_customers_pdf():
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        
        customers = Customer.query.all()
        customer_data = []
        
        for customer in customers:
            total_invoices = sum(invoice.amount for invoice in customer.sales_invoices)
            total_collections = sum(collection.amount for collection in customer.collections)
            customer_data.append([
                str(customer.id),
                customer.name,
                customer.phone or '-',
                customer.email or '-',
                f'{customer.balance:,.2f}',
                f'{total_invoices:,.2f}',
                f'{total_collections:,.2f}',
                customer.created_at.strftime('%Y-%m-%d')
            ])
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Title
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        title = Paragraph("تقارير العملاء", title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Table headers
        headers = ['الرقم', 'اسم العميل', 'الهاتف', 'البريد الإلكتروني', 'الرصيد', 'إجمالي الفواتير', 'إجمالي التحصيلات', 'تاريخ الإضافة']
        
        # Create table
        table_data = [headers] + customer_data
        table = Table(table_data)
        
        # Style the table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'تقارير_العملاء_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    except ImportError:
        flash('مكتبة reportlab غير مثبتة. يرجى تثبيتها لاستخدام تصدير PDF', 'error')
        return redirect(url_for('customer_reports'))
    except Exception as e:
        flash(f'حدث خطأ في تصدير PDF: {str(e)}', 'error')
        return redirect(url_for('customer_reports'))

# Export Supplier Reports to Excel
@app.route('/export_suppliers_excel')
@login_required
def export_suppliers_excel():
    try:
        import pandas as pd
        from io import BytesIO
        
        suppliers = Supplier.query.all()
        supplier_data = []
        
        for supplier in suppliers:
            total_invoices = sum(invoice.amount for invoice in supplier.purchase_invoices)
            total_payments = sum(payment.amount for payment in supplier.payments)
            supplier_data.append({
                'الرقم': supplier.id,
                'اسم المورد': supplier.name,
                'الهاتف': supplier.phone or '-',
                'البريد الإلكتروني': supplier.email or '-',
                'الرصيد': supplier.balance,
                'إجمالي الفواتير': total_invoices,
                'إجمالي المدفوعات': total_payments,
                'تاريخ الإضافة': supplier.created_at.strftime('%Y-%m-%d')
            })
        
        df = pd.DataFrame(supplier_data)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='تقارير الموردين', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'تقارير_الموردين_{datetime.now().strftime("%Y%m%d")}.xlsx'
        )
    except ImportError:
        flash('مكتبة pandas غير مثبتة. يرجى تثبيتها لاستخدام تصدير Excel', 'error')
        return redirect(url_for('supplier_reports'))
    except Exception as e:
        flash(f'حدث خطأ في تصدير Excel: {str(e)}', 'error')
        return redirect(url_for('supplier_reports'))

# View Sales Invoice
@app.route('/view_sales_invoice/<int:invoice_id>')
@login_required
def view_sales_invoice(invoice_id):
    invoice = SalesInvoice.query.get_or_404(invoice_id)
    return render_template('view_sales_invoice.html', invoice=invoice)

# Edit Sales Invoice
@app.route('/edit_sales_invoice/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def edit_sales_invoice(invoice_id):
    invoice = SalesInvoice.query.get_or_404(invoice_id)
    
    if request.method == 'POST':
        invoice.invoice_number = request.form['invoice_number']
        invoice.customer_id = request.form['customer_id']
        invoice.amount = float(request.form['amount'])
        invoice.invoice_date = datetime.strptime(request.form['invoice_date'], '%Y-%m-%d').date()
        invoice.description = request.form.get('description', '')
        
        # Update customer balance
        old_amount = invoice.amount
        new_amount = float(request.form['amount'])
        difference = new_amount - old_amount
        invoice.customer.balance += difference
        
        db.session.commit()
        flash('تم تحديث الفاتورة بنجاح!', 'success')
        return redirect(url_for('sales_invoices'))
    
    customers = Customer.query.all()
    return render_template('edit_sales_invoice.html', invoice=invoice, customers=customers)

# Print Sales Invoice
@app.route('/print_sales_invoice/<int:invoice_id>')
@login_required
def print_sales_invoice(invoice_id):
    invoice = SalesInvoice.query.get_or_404(invoice_id)
    return render_template('print_sales_invoice.html', invoice=invoice)

# View Purchase Invoice
@app.route('/view_purchase_invoice/<int:invoice_id>')
@login_required
def view_purchase_invoice(invoice_id):
    invoice = PurchaseInvoice.query.get_or_404(invoice_id)
    return render_template('view_purchase_invoice.html', invoice=invoice)

# Edit Purchase Invoice
@app.route('/edit_purchase_invoice/<int:invoice_id>', methods=['GET', 'POST'])
@login_required
def edit_purchase_invoice(invoice_id):
    invoice = PurchaseInvoice.query.get_or_404(invoice_id)
    
    if request.method == 'POST':
        invoice.invoice_number = request.form['invoice_number']
        invoice.supplier_id = request.form['supplier_id']
        invoice.amount = float(request.form['amount'])
        invoice.invoice_date = datetime.strptime(request.form['invoice_date'], '%Y-%m-%d').date()
        invoice.description = request.form.get('description', '')
        
        # Update supplier balance
        old_amount = invoice.amount
        new_amount = float(request.form['amount'])
        difference = new_amount - old_amount
        invoice.supplier.balance += difference
        
        db.session.commit()
        flash('تم تحديث الفاتورة بنجاح!', 'success')
        return redirect(url_for('purchase_invoices'))
    
    suppliers = Supplier.query.all()
    return render_template('edit_purchase_invoice.html', invoice=invoice, suppliers=suppliers)

# Print Purchase Invoice
@app.route('/print_purchase_invoice/<int:invoice_id>')
@login_required
def print_purchase_invoice(invoice_id):
    invoice = PurchaseInvoice.query.get_or_404(invoice_id)
    return render_template('print_purchase_invoice.html', invoice=invoice)

# View Collection
@app.route('/view_collection/<int:collection_id>')
@login_required
def view_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    return render_template('view_collection.html', collection=collection)

# Edit Collection
@app.route('/edit_collection/<int:collection_id>', methods=['GET', 'POST'])
@login_required
def edit_collection(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    
    if request.method == 'POST':
        old_amount = collection.amount
        collection.customer_id = request.form['customer_id']
        collection.amount = float(request.form['amount'])
        collection.collection_date = datetime.strptime(request.form['collection_date'], '%Y-%m-%d').date()
        collection.notes = request.form.get('notes', '')
        
        # Update customer balance
        new_amount = float(request.form['amount'])
        difference = new_amount - old_amount
        collection.customer.balance -= difference
        
        db.session.commit()
        flash('تم تحديث التحصيل بنجاح!', 'success')
        return redirect(url_for('collections'))
    
    customers = Customer.query.all()
    return render_template('edit_collection.html', collection=collection, customers=customers)

# Print Collection Receipt
@app.route('/print_collection_receipt/<int:collection_id>')
@login_required
def print_collection_receipt(collection_id):
    collection = Collection.query.get_or_404(collection_id)
    return render_template('print_collection_receipt.html', collection=collection)

# View Payment
@app.route('/view_payment/<int:payment_id>')
@login_required
def view_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    return render_template('view_payment.html', payment=payment)

# Edit Payment
@app.route('/edit_payment/<int:payment_id>', methods=['GET', 'POST'])
@login_required
def edit_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    if request.method == 'POST':
        old_amount = payment.amount
        payment.supplier_id = request.form['supplier_id']
        payment.amount = float(request.form['amount'])
        payment.payment_date = datetime.strptime(request.form['payment_date'], '%Y-%m-%d').date()
        payment.notes = request.form.get('notes', '')
        
        # Update supplier balance
        new_amount = float(request.form['amount'])
        difference = new_amount - old_amount
        payment.supplier.balance -= difference
        
        db.session.commit()
        flash('تم تحديث المدفوع بنجاح!', 'success')
        return redirect(url_for('payments'))
    
    suppliers = Supplier.query.all()
    return render_template('edit_payment.html', payment=payment, suppliers=suppliers)

# Print Payment Receipt
@app.route('/print_payment_receipt/<int:payment_id>')
@login_required
def print_payment_receipt(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    return render_template('print_payment_receipt.html', payment=payment)

# Export Supplier Reports to PDF
@app.route('/export_suppliers_pdf')
@login_required
def export_suppliers_pdf():
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from io import BytesIO
        
        suppliers = Supplier.query.all()
        supplier_data = []
        
        for supplier in suppliers:
            total_invoices = sum(invoice.amount for invoice in supplier.purchase_invoices)
            total_payments = sum(payment.amount for payment in supplier.payments)
            supplier_data.append([
                str(supplier.id),
                supplier.name,
                supplier.phone or '-',
                supplier.email or '-',
                f'{supplier.balance:,.2f}',
                f'{total_invoices:,.2f}',
                f'{total_payments:,.2f}',
                supplier.created_at.strftime('%Y-%m-%d')
            ])
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        
        # Title
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        title = Paragraph("تقارير الموردين", title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Table headers
        headers = ['الرقم', 'اسم المورد', 'الهاتف', 'البريد الإلكتروني', 'الرصيد', 'إجمالي الفواتير', 'إجمالي المدفوعات', 'تاريخ الإضافة']
        
        # Create table
        table_data = [headers] + supplier_data
        table = Table(table_data)
        
        # Style the table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        doc.build(elements)
        
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'تقارير_الموردين_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
    except ImportError:
        flash('مكتبة reportlab غير مثبتة. يرجى تثبيتها لاستخدام تصدير PDF', 'error')
        return redirect(url_for('supplier_reports'))
    except Exception as e:
        flash(f'حدث خطأ في تصدير PDF: {str(e)}', 'error')
        return redirect(url_for('supplier_reports'))

# Backup
@app.route('/backup')
@login_required
def backup():
    return render_template('backup.html')

# Initialize database and admin user
with app.app_context():
    db.create_all()
    
    # Create admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin_user)
        db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
