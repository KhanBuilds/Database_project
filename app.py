from flask import Flask, render_template, url_for, redirect, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import os
from dotenv import load_dotenv

app = Flask(__name__, template_folder='template')
app.config['SQLALCHEMY_DATABASE_URI']=os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)




class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(100), nullable=False)
    email= db.Column(db.String(100), unique=True)
    student_id= db.Column(db.Integer, unique=True)
    password= db.Column(db.String(100), nullable=False)

class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    employee_id = db.Column(db.String(20), unique=True)
    department = db.Column(db.String(100))
    password = db.Column(db.String(100), nullable=False)

class Book(db.Model):
    book_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))
    isbn = db.Column(db.String(20), unique=True)
    publisher = db.Column(db.String(255))
    year = db.Column(db.Integer)
    quantity = db.Column(db.Integer, default=0)
    available = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<Book {self.title}>'


class BorrowedBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    borrower_identifier = db.Column(db.String(50), unique=True, nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.book_id'), nullable=False)
    borrowed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    book = db.relationship('Book', backref='borrow_records')

    def __repr__(self):
        return f'<BorrowedBook {self.borrower_identifier} -> {self.book_id}>'

class Members(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(100), nullable=False)
    phone_number=db.Column(db.String(100), nullable=False)
    email=db.Column(db.String(100), unique=True, nullable=False)

class Issue(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    member_id=db.Column(db.Integer,db.ForeignKey('members.id'), nullable=False)
    book_id=db.Column(db.Integer,db.ForeignKey('book.book_id'), nullable=False)
    issue_date=db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=False)

    member=db.relationship('Members', backref='issued_books')
    book=db.relationship('Book', backref='issue_records')

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')
    

@app.route('/dashboard')
def dashboard():
    students = Student.query.all()
    faculty = Faculty.query.all()
    books = Book.query.all()
    borrowed_books = BorrowedBook.query.all()

    return render_template(
        'dashboard.html',
        students=students,
        faculty=faculty,
        books=books,
        borrowed_books=borrowed_books,
    )
@app.route('/library/books')
def manage_books():
    query = request.args.get('q', '').strip()
    field = request.args.get('field', 'title')
    sort = request.args.get('sort', 'title')

    books_query = Book.query

    if query:
        if field == 'title':
            books_query = books_query.filter(Book.title.ilike(f'%{query}%'))
        elif field == 'author':
            books_query = books_query.filter(Book.author.ilike(f'%{query}%'))
        elif field == 'category':
            books_query = books_query.filter(Book.category.ilike(f'%{query}%'))
        else:
            books_query = books_query.filter(Book.isbn.ilike(f'%{query}%'))

    if sort == 'author':
        books_query = books_query.order_by(Book.author.asc())
    else:
        books_query = books_query.order_by(Book.title.asc())

    books = books_query.all()

    return render_template(
        'books.html',
        books=books,
        query=query,
        field=field,
        sort=sort,
    )


@app.route('/library/books/add', methods = ['GET', 'POST'])
def register_books():
    if request.method == 'POST':
        title = request.form['title'].strip()
        author = request.form['author'].strip()
        category = request.form['category'].strip()
        isbn = request.form['isbn'].strip()
        publisher = request.form['publisher'].strip()
        year_text = request.form['year'].strip()
        quantity_text = request.form['quantity'].strip()

        if not title or not author or not isbn or not quantity_text:
            return render_template(
                'add_book.html',
                error='Title, author, ISBN, and quantity are required.',
            )

        try:
            year_value = int(year_text) if year_text else None
            quantity_value = int(quantity_text)
        except ValueError:
            return render_template(
                'add_book.html',
                error='Year and quantity must be valid numbers.',
            )

        new_book= Book(
            title = title,
            author = author,
            category = category,
            isbn = isbn,
            publisher = publisher,
            year = year_value,
            quantity = quantity_value,
            available = quantity_value
        )
        try:
            db.session.add(new_book)
            db.session.commit()
            return redirect(url_for('manage_books'))
        except IntegrityError:
            db.session.rollback()
            return render_template(
                'add_book.html',
                error='Book already exists.',
            )

    return render_template('add_book.html', error=None)


@app.route('/library/books/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    book = Book.query.filter_by(book_id=book_id).first()
    if not book:
        return render_template(
            'edit_book.html',
            book=None,
            error='Book not found.',
        )

    if request.method == 'POST':
        title = request.form['title'].strip()
        author = request.form['author'].strip()
        category = request.form['category'].strip()
        publisher = request.form['publisher'].strip()
        year_text = request.form['year'].strip()
        quantity_text = request.form['quantity'].strip()

        if not title or not author or not quantity_text:
            return render_template(
                'edit_book.html',
                book=book,
                error='Title, author, and quantity are required.',
            )

        try:
            year_value = int(year_text) if year_text else None
            quantity_value = int(quantity_text)
        except ValueError:
            return render_template(
                'edit_book.html',
                book=book,
                error='Year and quantity must be valid numbers.',
            )

        book.title = title
        book.author = author
        book.category = category
        book.publisher = publisher
        book.year = year_value
        book.quantity = quantity_value
        book.available = quantity_value

        try:
            db.session.commit()
            return redirect(url_for('manage_books'))
        except IntegrityError:
            db.session.rollback()
            return render_template(
                'edit_book.html',
                book=book,
                error='Could not update book.',
            )

    return render_template('edit_book.html', book=book, error=None)


@app.route('/library/books/delete/<int:book_id>', methods=['GET', 'POST'])
def delete_book(book_id):
    book = Book.query.filter_by(book_id=book_id).first()
    if not book:
        return render_template(
            'delete_book.html',
            book=None,
            error='Book not found.',
        )

    if request.method == 'POST':
        decision = request.form.get('confirm')

        if decision == 'yes':
            db.session.delete(book)
            db.session.commit()

        return redirect(url_for('manage_books'))

    return render_template('delete_book.html', book=book, error=None)

@app.route('/library/borrow', methods=['GET', 'POST'])
def borrow_books():
    if request.method == 'POST':
        borrower_identifier = request.form['borrower_identifier']
        book_id = int(request.form['book_id'])

        existing_borrower = BorrowedBook.query.filter_by(borrower_identifier=borrower_identifier).first()
        if existing_borrower:
            return render_template(
                'borrow_book.html',
                error=f'{borrower_identifier} already has a borrowed book. Limit is 1 book per person.',
                success=None,
            )

        book = Book.query.filter_by(book_id=book_id).first()
        if not book:
            return render_template(
                'borrow_book.html',
                error='No book was found for that Book ID.',
                success=None,
            )

        if book.available < 1:
            return render_template(
                'borrow_book.html',
                error=f'No available copies of {book.title} right now.',
                success=None,
            )

        borrow_record = BorrowedBook(
            borrower_identifier=borrower_identifier,
            book_id=book.book_id
        )
        book.available -= 1
        try:
            db.session.add(borrow_record)
            db.session.commit()
            return render_template(
                'borrow_book.html',
                error=None,
                success=f'{borrower_identifier} borrowed 1 copy of {book.title}. {book.available} remaining.',
            )
        except IntegrityError:
            db.session.rollback()
            return render_template(
                'borrow_book.html',
                error='Could not borrow book. Please try again.',
                success=None,
            )

    return render_template('borrow_book.html', error=None, success=None)

@app.route('/reg/student', methods=['GET','POST'])
def register_student():
    if request.method == 'POST':
        new_student= Student(
            name = request.form['name'],
            email= request.form['email'],
            student_id= request.form['sid'],
            password=request.form['password']
        )
        try:
            db.session.add(new_student)
            db.session.commit()
            return redirect(url_for('dashboard'))
        except IntegrityError:
            db.session.rollback() # This clears the "failed" transaction
            return render_template(
                'register_student.html',
                error='Email or Student ID already exists.',
            )
    
    return render_template('register_student.html', error=None)
@app.route('/reg/faculty', methods=['GET', 'POST'])
def register_faculty():
    if request.method == 'POST':
        new_faculty = Faculty(
            name=request.form['name'],
            email=request.form['email'],
            employee_id=request.form['eid'],
            department=request.form['dept'],
            password=request.form['password']
        )
        db.session.add(new_faculty)
        db.session.commit()
        return render_template(
            'register_faculty.html',
            success='Faculty registered successfully.',
        )

    return render_template('register_faculty.html', success=None)



if __name__ == '__main__':
    app.run(debug=True)