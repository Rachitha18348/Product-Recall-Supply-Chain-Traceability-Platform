from flask import Flask, render_template, request, redirect, url_for, session
from database import get_db_connection
import bcrypt
from mail import send_email
import random
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("home.html")


# =========================
# AUTHENTICATION
# =========================



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not name or not email or not password:
            return render_template(
                "register.html",
                error="All fields are required."
            )

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            query = """
                INSERT INTO users (name, email, password, role)
                VALUES (%s, %s, %s, %s)
            """

            cursor.execute(
                query,
                (
                    name,
                    email,
                    hashed_password.decode("utf-8"),
                    "Admin"
                )
            )

            connection.commit()
            return redirect(url_for("login"))

        except Exception:
            connection.rollback()
            return render_template(
                "register.html",
                error="Registration failed. This email may already be registered."
            )

        finally:
            cursor.close()
            connection.close()

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = "SELECT * FROM users WHERE email = %s"

        cursor.execute(query, (email,))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and bcrypt.checkpw(
            password.encode("utf-8"),
            user["password"].encode("utf-8")
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("dashboard"))

        return "Invalid email or password"

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if not user:
            return "Email not registered"

        otp = str(random.randint(100000, 999999))

        session["reset_email"] = email
        session["reset_otp"] = otp

        subject = "ProductTrace Password Reset OTP"

        message = f"""
Hello {user['name']},

Your ProductTrace password reset OTP is:

{otp}

This OTP is required to reset your password.

If you did not request a password reset, please ignore this email.

Regards,
ProductTrace Team
"""

        send_email(email, subject, message)

        return redirect(url_for("verify_otp"))

    return render_template("forgot_password.html")

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form["otp"]

        if entered_otp == session.get("reset_otp"):

            session["otp_verified"] = True

            return redirect(url_for("reset_password"))

        return "Invalid OTP"

    return render_template("verify_otp.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():

    if not session.get("otp_verified"):
        return redirect(url_for("forgot_password"))

    if request.method == "POST":

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return "Passwords do not match"

        email = session.get("reset_email")

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE users
            SET password = %s
            WHERE email = %s
            """,
            (
                hashed_password.decode("utf-8"),
                email
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        session.pop("reset_email", None)
        session.pop("reset_otp", None)
        session.pop("otp_verified", None)

        return redirect(url_for("login"))

    return render_template("reset_password.html")
# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS count FROM production_batches")
    total_batches = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM products")
    total_products = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM products
        WHERE status = 'Defective'
    """)
    defective_products = cursor.fetchone()["count"]

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM recalls
        WHERE status = 'Initiated'
    """)
    active_recalls = cursor.fetchone()["count"]

    cursor.close()
    connection.close()

    return render_template(
        "dashboard.html",
        total_batches=total_batches,
        total_products=total_products,
        defective_products=defective_products,
        active_recalls=active_recalls
    )

# =========================
# SUPPLY CHAIN
# =========================

@app.route("/raw-materials")
def raw_materials():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM raw_materials
        ORDER BY id DESC
    """)

    materials = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "raw_materials.html",
        materials=materials
    )

@app.route("/raw-materials/add", methods=["GET", "POST"])
def add_raw_material():

    if request.method == "POST":

        name = request.form["name"]
        supplier_name = request.form["supplier_name"]
        quantity = request.form["quantity"]
        unit = request.form["unit"]
        received_date = request.form["received_date"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO raw_materials
            (name, supplier_name, quantity, unit, received_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            name,
            supplier_name,
            quantity,
            unit,
            received_date
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("raw_materials"))

    return render_template("add_raw_material.html")

@app.route("/batches")
def batches():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM production_batches
        ORDER BY id DESC
    """)

    batches = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "batches.html",
        batches=batches
    )

@app.route("/batches/add", methods=["GET", "POST"])
def add_batch():

    if request.method == "POST":

        batch_number = request.form["batch_number"]
        product_name = request.form["product_name"]
        production_date = request.form["production_date"]
        quantity = request.form["quantity"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO production_batches
            (batch_number, product_name, production_date, quantity)
            VALUES (%s, %s, %s, %s)
        """, (
            batch_number,
            product_name,
            production_date,
            quantity
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("batches"))

    return render_template("add_batch.html")

@app.route("/products")
def products():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            products.id,
            products.product_code,
            production_batches.batch_number,
            products.manufacturing_date,
            products.status
        FROM products
        JOIN production_batches
            ON products.batch_id = production_batches.id
        ORDER BY products.id DESC
    """)

    products = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "products.html",
        products=products
    )
@app.route("/products/add", methods=["GET", "POST"])
def add_product():

    if request.method == "POST":

        product_code = request.form["product_code"]
        batch_id = request.form["batch_id"]
        manufacturing_date = request.form["manufacturing_date"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO products
            (product_code, batch_id, manufacturing_date)
            VALUES (%s, %s, %s)
        """, (
            product_code,
            batch_id,
            manufacturing_date
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("products"))

    return render_template("add_product.html")

@app.route("/quality-inspection")
def quality_inspection():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            quality_inspections.id,
            production_batches.batch_number,
            quality_inspections.inspection_date,
            quality_inspections.inspector_name,
            quality_inspections.result,
            quality_inspections.remarks
        FROM quality_inspections
        JOIN production_batches
            ON quality_inspections.batch_id = production_batches.id
        ORDER BY quality_inspections.id DESC
    """)

    inspections = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "quality_inspection.html",
        inspections=inspections
    )

@app.route("/quality-inspection/add", methods=["GET", "POST"])
def add_inspection():

    if request.method == "POST":

        batch_id = request.form["batch_id"]
        inspection_date = request.form["inspection_date"]
        inspector_name = request.form["inspector_name"]
        result = request.form["result"]
        remarks = request.form["remarks"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO quality_inspections
            (batch_id, inspection_date, inspector_name, result, remarks)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            batch_id,
            inspection_date,
            inspector_name,
            result,
            remarks
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("quality_inspection"))

    return render_template("add_inspection.html")


@app.route("/warehouses")
def warehouse():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM warehouses
        ORDER BY id DESC
    """)

    warehouses = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "warehouse.html",
        warehouses=warehouses
    )


@app.route("/warehouses/add", methods=["GET", "POST"])
def add_warehouse():
    if request.method == "POST":
        name = request.form["name"]
        location = request.form["location"]
        manager_name = request.form["manager_name"]
        contact = request.form["contact"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO warehouses
            (name, location, manager_name, contact)
            VALUES (%s, %s, %s, %s)
        """, (name, location, manager_name, contact))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("warehouse"))

    return render_template("add_warehouse.html")





@app.route("/distributors")
def distributors():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM distributors
        ORDER BY id DESC
    """)

    distributors = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "distributors.html",
        distributors=distributors
    )


@app.route("/distributors/add", methods=["GET", "POST"])
def add_distributor():
    if request.method == "POST":
        name = request.form["name"]
        location = request.form["location"]
        contact = request.form["contact"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO distributors (name, contact, location)
            VALUES (%s, %s, %s)
        """, (name, contact, location))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("distributors"))

    return render_template("add_distributor.html")





@app.route("/retailers")
def retailers():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM retailers
        ORDER BY id DESC
    """)

    retailers = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "retailers.html",
        retailers=retailers
    )


@app.route("/retailers/add", methods=["GET", "POST"])
def add_retailer():
    if request.method == "POST":
        name = request.form["name"]
        location = request.form["location"]
        contact = request.form["contact"]

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO retailers (name, contact, location)
            VALUES (%s, %s, %s)
        """, (name, contact, location))

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for("retailers"))

    return render_template("add_retailer.html")








# =========================
# PRODUCT TRACEABILITY
# =========================





@app.route("/traceability", methods=["GET", "POST"])
def traceability():
    trace_data = None
    products = []
    movements = []
    error = None
    search_type = ""
    search_value = ""

    if request.method == "POST":
        search_type = request.form.get("search_type", "").strip().lower()
        search_value = request.form.get("search_value", "").strip()

        if not search_value:
            error = "Please enter a batch number or product code."
        else:
            connection = None
            cursor = None

            try:
                connection = get_db_connection()
                cursor = connection.cursor(dictionary=True)

                if search_type == "batch":
                    cursor.execute("""
                        SELECT id, batch_number, product_name,
                               production_date, quantity, status
                        FROM production_batches
                        WHERE TRIM(batch_number) = %s
                    """, (search_value,))

                    trace_data = cursor.fetchone()

                    if trace_data:
                        cursor.execute("""
                            SELECT id, product_code,
                                   manufacturing_date, status
                            FROM products
                            WHERE batch_id = %s
                            ORDER BY id
                        """, (trace_data["id"],))
                        products = cursor.fetchall()

                        cursor.execute("""
                            SELECT p.product_code,
                                   pm.from_location,
                                   pm.to_location,
                                   pm.movement_date,
                                   pm.status
                            FROM product_movements AS pm
                            JOIN products AS p ON pm.product_id = p.id
                            WHERE p.batch_id = %s
                            ORDER BY pm.movement_date, pm.id
                        """, (trace_data["id"],))
                        movements = cursor.fetchall()

                elif search_type == "product":
                    cursor.execute("""
                        SELECT p.id, p.product_code,
                               p.manufacturing_date, p.status,
                               b.batch_number, b.product_name,
                               b.production_date, b.quantity
                        FROM products AS p
                        JOIN production_batches AS b
                          ON p.batch_id = b.id
                        WHERE TRIM(p.product_code) = %s
                    """, (search_value,))

                    trace_data = cursor.fetchone()

                    if trace_data:
                        products = [{
                            "product_code": trace_data["product_code"],
                            "manufacturing_date": trace_data["manufacturing_date"],
                            "status": trace_data["status"]
                        }]

                        cursor.execute("""
                            SELECT p.product_code,
                                   pm.from_location,
                                   pm.to_location,
                                   pm.movement_date,
                                   pm.status
                            FROM product_movements AS pm
                            JOIN products AS p ON pm.product_id = p.id
                            WHERE p.id = %s
                            ORDER BY pm.movement_date, pm.id
                        """, (trace_data["id"],))
                        movements = cursor.fetchall()

                else:
                    error = "Please select a valid trace type."

                if trace_data is None and error is None:
                    error = "No matching batch or product was found."

            except Exception as e:
                print("Traceability error:", e)
                error = "An error occurred while searching. Check the Flask terminal."

            finally:
                if cursor is not None:
                    cursor.close()
                if connection is not None:
                    connection.close()

    return render_template(
        "traceability.html",
        trace_data=trace_data,
        products=products,
        movements=movements,
        error=error,
        search_type=search_type,
        search_value=search_value
    )




@app.route("/traceability/batch")
def batch_traceability():
    return "Batch Traceability"


@app.route("/traceability/product")
def product_traceability():
    return "Individual Product Traceability"


# =========================
# DEFECT REPORTS
# =========================


@app.route("/defect-reports")
def defect_reports():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                defect_reports.id,
                production_batches.batch_number,
                products.product_code,
                defect_reports.defect_type,
                defect_reports.reported_by,
                defect_reports.reported_date,
                defect_reports.status
            FROM defect_reports
            LEFT JOIN production_batches
                ON defect_reports.batch_id = production_batches.id
            LEFT JOIN products
                ON defect_reports.product_id = products.id
            ORDER BY defect_reports.id DESC
        """)

        defects = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "defect_reports.html",
        defects=defects
    )




@app.route("/defect-reports/add", methods=["GET", "POST"])
def add_defect_report():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            report_target = request.form.get("report_target", "").strip()
            reported_by = request.form.get("reported_by", "").strip()
            batch_id = request.form.get("batch_id") or None
            product_id = request.form.get("product_id") or None
            defect_type = request.form.get("defect_type", "").strip()
            description = request.form.get("description", "").strip()
            reported_date = request.form.get("reported_date", "").strip()

            if report_target == "batch":
                product_id = None
                if not batch_id:
                    raise ValueError("Please select a production batch.")

            elif report_target == "product":
                batch_id = None
                if not product_id:
                    raise ValueError("Please select an individual product.")

            else:
                raise ValueError("Please select a valid report target.")

            if not reported_by or not defect_type or not description or not reported_date:
                raise ValueError("Please fill in all required fields.")

            cursor.execute("""
                INSERT INTO defect_reports
                    (batch_id, product_id, reported_by, defect_type,
                     description, reported_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                batch_id,
                product_id,
                reported_by,
                defect_type,
                description,
                reported_date,
                "Reported"
            ))

            connection.commit()
            return redirect(url_for("defect_reports"))

        cursor.execute("""
            SELECT id, batch_number, product_name
            FROM production_batches
            ORDER BY id DESC
        """)
        batches = cursor.fetchall()

        cursor.execute("""
            SELECT id, product_code
            FROM products
            ORDER BY id DESC
        """)
        products = cursor.fetchall()

        return render_template(
            "add_defect_report.html",
            batches=batches,
            products=products
        )

    except ValueError as e:
        connection.rollback()

        cursor.execute("""
            SELECT id, batch_number, product_name
            FROM production_batches
            ORDER BY id DESC
        """)
        batches = cursor.fetchall()

        cursor.execute("""
            SELECT id, product_code
            FROM products
            ORDER BY id DESC
        """)
        products = cursor.fetchall()

        return render_template(
            "add_defect_report.html",
            batches=batches,
            products=products,
            error=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# RECALL MANAGEMENT
# =========================


@app.route("/recalls")
def recalls():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                recalls.id,
                recalls.recall_type,
                production_batches.batch_number,
                products.product_code,
                recalls.reason,
                recalls.recall_date,
                recalls.status
            FROM recalls
            LEFT JOIN production_batches
                ON recalls.batch_id = production_batches.id
            LEFT JOIN products
                ON recalls.product_id = products.id
            ORDER BY recalls.id DESC
        """)

        recall_records = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "recalls.html",
        recalls=recall_records
    )


@app.route("/recalls/add", methods=["GET", "POST"])
def add_recall():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            recall_type = request.form.get("recall_type", "").strip()
            batch_id = request.form.get("batch_id") or None
            product_id = request.form.get("product_id") or None
            reason = request.form.get("reason", "").strip()
            recall_date = request.form.get("recall_date", "").strip()

            if recall_type == "Batch":
                product_id = None
                if not batch_id:
                    raise ValueError("Please select a production batch.")

            elif recall_type == "Product":
                batch_id = None
                if not product_id:
                    raise ValueError("Please select an individual product.")

            else:
                raise ValueError("Please select a valid recall type.")

            if not reason or not recall_date:
                raise ValueError("Please enter the recall reason and date.")

            cursor.execute("""
                INSERT INTO recalls
                    (recall_type, batch_id, product_id, reason,
                     recall_date, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                recall_type,
                batch_id,
                product_id,
                reason,
                recall_date,
                "Initiated"
            ))

            connection.commit()
            return redirect(url_for("recalls"))

        cursor.execute("""
            SELECT id, batch_number, product_name
            FROM production_batches
            ORDER BY id DESC
        """)
        batches = cursor.fetchall()

        cursor.execute("""
            SELECT id, product_code
            FROM products
            ORDER BY id DESC
        """)
        products = cursor.fetchall()

        return render_template(
            "add_recall.html",
            batches=batches,
            products=products
        )

    except ValueError as e:
        connection.rollback()

        cursor.execute("""
            SELECT id, batch_number, product_name
            FROM production_batches
            ORDER BY id DESC
        """)
        batches = cursor.fetchall()

        cursor.execute("""
            SELECT id, product_code
            FROM products
            ORDER BY id DESC
        """)
        products = cursor.fetchall()

        return render_template(
            "add_recall.html",
            batches=batches,
            products=products,
            error=str(e)
        )

    finally:
        cursor.close()
        connection.close()



@app.route("/recall/returns")
def returned_products():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                returned_products.id,
                returned_products.recall_id,
                products.product_code,
                returned_products.returned_by,
                returned_products.return_date,
                returned_products.condition_description,
                returned_products.status
            FROM returned_products
            JOIN products
                ON returned_products.product_id = products.id
            ORDER BY returned_products.id DESC
        """)

        returned_items = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "returned_products.html",
        returned_items=returned_items
    )


@app.route("/recall/returns/add", methods=["GET", "POST"])
def add_returned_product():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        if request.method == "POST":
            recall_id = request.form.get("recall_id", "").strip()
            product_id = request.form.get("product_id", "").strip()
            returned_by = request.form.get("returned_by", "").strip()
            return_date = request.form.get("return_date", "").strip()
            condition_description = request.form.get(
                "condition_description", ""
            ).strip()

            if not all([
                recall_id,
                product_id,
                returned_by,
                return_date,
                condition_description
            ]):
                raise ValueError("Please fill in all required fields.")

            # Confirm that the selected recall exists.
            cursor.execute(
                "SELECT id, recall_type, batch_id, product_id "
                "FROM recalls WHERE id = %s",
                (recall_id,)
            )
            recall = cursor.fetchone()

            if not recall:
                raise ValueError("Please select a valid recall.")

            # Confirm that the selected product exists.
            cursor.execute(
                "SELECT id, batch_id FROM products WHERE id = %s",
                (product_id,)
            )
            product = cursor.fetchone()

            if not product:
                raise ValueError("Please select a valid product.")

            # Ensure the returned product belongs to the recall.
            if recall["recall_type"].lower() == "batch":
                if product["batch_id"] != recall["batch_id"]:
                    raise ValueError(
                        "Select a product from the recalled batch."
                    )
            elif recall["recall_type"].lower() == "product":
                if product["id"] != recall["product_id"]:
                    raise ValueError(
                        "Select the individual product specified in the recall."
                    )
            else:
                raise ValueError("The recall type is not supported.")

            cursor.execute("""
                INSERT INTO returned_products
                    (recall_id, product_id, returned_by, return_date,
                     condition_description, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                recall_id,
                product_id,
                returned_by,
                return_date,
                condition_description,
                "Received"
            ))

            connection.commit()
            return redirect(url_for("returned_products"))

        cursor.execute("""
            SELECT
                recalls.id,
                recalls.recall_type,
                recalls.batch_id,
                recalls.product_id,
                production_batches.batch_number,
                products.product_code
            FROM recalls
            LEFT JOIN production_batches
                ON recalls.batch_id = production_batches.id
            LEFT JOIN products
                ON recalls.product_id = products.id
            ORDER BY recalls.id DESC
        """)
        recalls = cursor.fetchall()

        cursor.execute("""
            SELECT id, product_code, batch_id
            FROM products
            ORDER BY id DESC
        """)
        products = cursor.fetchall()

        return render_template(
            "add_returned_product.html",
            recalls=recalls,
            products=products
        )

    except ValueError as e:
        connection.rollback()

        cursor.execute("""
            SELECT
                recalls.id,
                recalls.recall_type,
                recalls.batch_id,
                recalls.product_id,
                production_batches.batch_number,
                products.product_code
            FROM recalls
            LEFT JOIN production_batches
                ON recalls.batch_id = production_batches.id
            LEFT JOIN products
                ON recalls.product_id = products.id
            ORDER BY recalls.id DESC
        """)
        recalls = cursor.fetchall()

        cursor.execute("""
            SELECT id, product_code, batch_id
            FROM products
            ORDER BY id DESC
        """)
        products = cursor.fetchall()

        return render_template(
            "add_returned_product.html",
            recalls=recalls,
            products=products,
            error=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# REPORTS
# =========================

@app.route("/recall/report")
def recall_report():
    return "Recall Report"


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":
    app.run(debug=True)