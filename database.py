# ============================================================
# DATABASE MODULE
# SnapReport
# ============================================================

# sqlite3 is Python's built-in library for working with
# SQLite databases.
import sqlite3


# Path helps us create reliable file paths.
from pathlib import Path


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# Get the directory where this database.py file is located.
#
# This ensures that the database stays inside the project folder.
BASE_DIR = Path(__file__).resolve().parent


# Path to our SQLite database.
#
# The database will be:
#
# ICRP_report-generator/
# └── icrp.db
#
DATABASE = BASE_DIR / "icrp.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db_connection():
    """
    Create and return a connection to the SQLite database.
    """

    # Open the SQLite database.
    connection = sqlite3.connect(DATABASE)

    # Allow us to access database columns by name.
    #
    # Example:
    #
    # template["name"]
    #
    # instead of:
    #
    # template[1]
    connection.row_factory = sqlite3.Row

    # Enable foreign-key support.
    #
    # This allows report_fields to properly reference
    # report_templates.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():
    """
    Create all required database tables.

    If the tables already exist, SQLite leaves them unchanged.
    """

    connection = get_db_connection()


    # ========================================================
    # REPORT TEMPLATES TABLE
    # ========================================================
    #
    # Stores the general information about a report.
    #
    # Example:
    #
    # Report Type:   ICRP Report
    # School:        Mengo Senior School
    # Year:          2026
    # Term:          Term 1
    #

    connection.execute("""
        CREATE TABLE IF NOT EXISTS report_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Name/type of the report.
            name TEXT NOT NULL,

            -- School using the report.
            school_name TEXT,

            -- Academic year.
            academic_year TEXT,

            -- Term or semester.
            term TEXT,

            -- Date and time the template was created.
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ========================================================
    # REPORT FIELDS TABLE
    # ========================================================
    #
    # Stores the individual fields belonging to a template.
    #
    # Examples:
    #
    # Student Name
    # Registration Number
    # Gender
    # Online Assessment
    # Physical Exam
    # Teacher Comment
    #

    connection.execute("""
        CREATE TABLE IF NOT EXISTS report_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- ID of the report template this field belongs to.
            template_id INTEGER NOT NULL,

            -- Name displayed by SnapReport.
            field_name TEXT NOT NULL,

            -- Matching column name in the Excel file.
            excel_column TEXT NOT NULL,

            -- Type of information stored in this field.
            field_type TEXT NOT NULL DEFAULT 'text',

            -- Whether this field must exist in the Excel file.
            -- SQLite stores False as 0 and True as 1.
            required INTEGER NOT NULL DEFAULT 0,

            -- Whether this field participates in grading.
            include_in_grading INTEGER NOT NULL DEFAULT 0,

            -- Controls the order in which fields appear.
            display_order INTEGER NOT NULL DEFAULT 0,

            -- Connect this field to its report template.
            --
            -- ON DELETE CASCADE means that if a template
            -- is deleted, its fields can also be deleted.
            FOREIGN KEY (template_id)
                REFERENCES report_templates(id)
                ON DELETE CASCADE
        )
    """)


    # ========================================================
    # GRADE BOUNDARIES TABLE
    # ========================================================
    #
    # Stores configurable grading rules for each template.
    #
    # Example:
    #
    # 80 - 100  -> A  -> Excellent
    # 70 - 79   -> B  -> Very Good
    # 60 - 69   -> C  -> Good
    #

    connection.execute("""
        CREATE TABLE IF NOT EXISTS grade_boundaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Which template this grading rule belongs to.
            template_id INTEGER NOT NULL,

            -- Minimum score for this grade (inclusive).
            min_score REAL NOT NULL,

            -- Maximum score for this grade (inclusive).
            max_score REAL NOT NULL,

            -- The grade label (e.g. A+, A, B).
            grade TEXT NOT NULL,

            -- Description of this grade (e.g. Excellent).
            remark TEXT NOT NULL DEFAULT '',

            -- Controls display order in the UI.
            display_order INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (template_id)
                REFERENCES report_templates(id)
                ON DELETE CASCADE
        )
    """)


    # ========================================================
    # GENERATED REPORTS TABLE
    # ========================================================
    #
    # Tracks each time a report is generated from a template.
    #
    # Example:
    #
    # Template 5  ->  Uploaded  ->  24 students  ->  Generated
    #

    connection.execute("""
        CREATE TABLE IF NOT EXISTS generated_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Which template was used.
            template_id INTEGER NOT NULL,

            -- Original filename uploaded by the user.
            filename TEXT NOT NULL,

            -- Number of students processed.
            student_count INTEGER NOT NULL DEFAULT 0,

            -- Path to the generated PDF.
            pdf_path TEXT,

            -- JSON string of processed student data.
            processed_data TEXT,

            -- When this report was generated.
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (template_id)
                REFERENCES report_templates(id)
                ON DELETE CASCADE
        )
    """)


    # Add processed_data column if missing (migration).
    try:
        connection.execute(
            "ALTER TABLE generated_reports ADD COLUMN processed_data TEXT"
        )
        connection.commit()
    except Exception:
        pass  # Column already exists.


    # Save database changes.
    connection.commit()

    # Close the connection.
    connection.close()


# ============================================================
# CREATE REPORT TEMPLATE
# ============================================================

def create_report_template(
    name,
    school_name,
    academic_year,
    term
):
    """
    Create a new report template.

    Returns:
        The ID of the newly-created template.
    """

    connection = get_db_connection()

    cursor = connection.execute("""
        INSERT INTO report_templates
        (
            name,
            school_name,
            academic_year,
            term
        )
        VALUES (?, ?, ?, ?)
    """, (
        name,
        school_name,
        academic_year,
        term
    ))

    connection.commit()

    # Get SQLite's automatically generated ID.
    template_id = cursor.lastrowid

    connection.close()

    return template_id


# ============================================================
# GET ONE REPORT TEMPLATE
# ============================================================

def get_report_template(template_id):
    """
    Retrieve one report template using its ID.
    """

    connection = get_db_connection()

    template = connection.execute("""
        SELECT *
        FROM report_templates
        WHERE id = ?
    """, (template_id,)).fetchone()

    connection.close()

    return template

# ============================================================
# GET ALL REPORT TEMPLATES
# ============================================================

def get_all_templates():
    """
    Retrieve all report templates with a count
    of how many fields each one has.

    Returns a list of rows, each containing:
        id, name, school_name, academic_year,
        term, created_at, field_count
    """

    connection = get_db_connection()

    templates = connection.execute("""
        SELECT
            t.id,
            t.name,
            t.school_name,
            t.academic_year,
            t.term,
            t.created_at,
            COUNT(f.id) as field_count
        FROM report_templates t
        LEFT JOIN report_fields f
            ON f.template_id = t.id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """).fetchall()

    connection.close()

    return templates

# ============================================================
# ADD REPORT FIELD
# ============================================================

def add_report_field(
    template_id,
    field_name,
    excel_column,
    field_type="text",
    required=False,
    include_in_grading=False,
    display_order=0
):
    """
    Add a new field to an existing report template.

    Returns:
        The ID of the newly-created field.
    """

    connection = get_db_connection()

    cursor = connection.execute("""
        INSERT INTO report_fields
        (
            template_id,
            field_name,
            excel_column,
            field_type,
            required,
            include_in_grading,
            display_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        template_id,
        field_name,
        excel_column,
        field_type,

        # Convert Python Boolean to SQLite 0/1.
        int(required),

        # Convert Python Boolean to SQLite 0/1.
        int(include_in_grading),

        display_order
    ))

    connection.commit()

    field_id = cursor.lastrowid

    connection.close()

    return field_id


# ============================================================
# GET ALL REPORT FIELDS
# ============================================================

def get_report_fields(template_id):
    """
    Retrieve all fields belonging to a specific template.

    Fields are ordered by display_order.
    """

    connection = get_db_connection()

    fields = connection.execute("""
        SELECT *
        FROM report_fields
        WHERE template_id = ?
        ORDER BY display_order ASC, id ASC
    """, (template_id,)).fetchall()

    connection.close()

    return fields


# ============================================================
# GET ONE REPORT FIELD
# ============================================================

def get_report_field(field_id):
    """
    Retrieve one report field using its ID.

    This is mainly used when editing an existing field.
    """

    connection = get_db_connection()

    field = connection.execute("""
        SELECT *
        FROM report_fields
        WHERE id = ?
    """, (field_id,)).fetchone()

    connection.close()

    return field


# ============================================================
# UPDATE REPORT FIELD
# ============================================================

def update_report_field(
    field_id,
    field_name,
    excel_column,
    field_type,
    required,
    include_in_grading,
    display_order
):
    """
    Update an existing report field.
    """

    connection = get_db_connection()

    connection.execute("""
        UPDATE report_fields
        SET
            field_name = ?,
            excel_column = ?,
            field_type = ?,
            required = ?,
            include_in_grading = ?,
            display_order = ?
        WHERE id = ?
    """, (
        field_name,
        excel_column,
        field_type,

        # Convert Boolean to SQLite 0/1.
        int(required),

        # Convert Boolean to SQLite 0/1.
        int(include_in_grading),

        display_order,

        # Identify the field to update.
        field_id
    ))

    connection.commit()

    connection.close()


# ============================================================
# DELETE REPORT FIELD
# ============================================================

def delete_report_field(field_id):
    """
    Delete one report field from the database.

    Returns:
        True if a field was deleted.
        False if no field with that ID existed.
    """

    connection = get_db_connection()

    cursor = connection.execute("""
        DELETE FROM report_fields
        WHERE id = ?
    """, (field_id,))

    # Save the deletion.
    connection.commit()

    # rowcount tells us whether SQLite actually deleted
    # a record.
    deleted = cursor.rowcount > 0

    connection.close()

    return deleted
# ============================================================
# DELETE REPORT TEMPLATE
# ============================================================

def delete_report_template(template_id):
    """
    Delete one report template and all its fields.

    The ON DELETE CASCADE constraint on report_fields
    means deleting the template automatically removes
    its fields too.

    Returns:
        True if a template was deleted.
        False if no template with that ID existed.
    """

    connection = get_db_connection()

    cursor = connection.execute("""
        DELETE FROM report_templates
        WHERE id = ?
    """, (template_id,))

    connection.commit()

    deleted = cursor.rowcount > 0

    connection.close()

    return deleted

# ============================================================
# GRADE BOUNDARIES — GET ALL
# ============================================================

def get_grade_boundaries(template_id):
    """
    Retrieve all grade boundaries for a template,
    ordered from highest score to lowest.
    """

    connection = get_db_connection()

    boundaries = connection.execute("""
        SELECT *
        FROM grade_boundaries
        WHERE template_id = ?
        ORDER BY min_score DESC
    """, (template_id,)).fetchall()

    connection.close()

    return boundaries


# ============================================================
# GRADE BOUNDARIES — SAVE ALL
# ============================================================

def save_grade_boundaries(template_id, boundaries):
    """
    Replace all grade boundaries for a template.

    This deletes existing boundaries and inserts new ones.
    """

    connection = get_db_connection()

    # Delete existing boundaries for this template.
    connection.execute("""
        DELETE FROM grade_boundaries
        WHERE template_id = ?
    """, (template_id,))

    # Insert new boundaries.
    for i, b in enumerate(boundaries):
        connection.execute("""
            INSERT INTO grade_boundaries
            (
                template_id,
                min_score,
                max_score,
                grade,
                remark,
                display_order
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            template_id,
            b['min_score'],
            b['max_score'],
            b['grade'],
            b['remark'],
            i
        ))

    connection.commit()
    connection.close()


# ============================================================
# GRADE LOOKUP — APPLY BOUNDARIES
# ============================================================

def apply_grading(template_id, score):
    """
    Look up the grade for a given score using
    the template's grade boundaries.

    Returns a tuple: (grade, remark)
    Falls back to 'N/A' if no boundaries exist.
    """

    boundaries = get_grade_boundaries(template_id)

    if not boundaries:
        return ('N/A', 'No grading configured')

    for b in boundaries:
        if b['min_score'] <= score <= b['max_score']:
            return (b['grade'], b['remark'])

    return ('N/A', 'Score out of range')


# ============================================================
# GENERATED REPORTS — CREATE
# ============================================================

def create_generated_report(
    template_id,
    filename,
    student_count,
    pdf_path=None,
    processed_data=None
):
    """
    Record a newly generated report.
    """

    connection = get_db_connection()

    cursor = connection.execute("""
        INSERT INTO generated_reports
        (
            template_id,
            filename,
            student_count,
            pdf_path,
            processed_data
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        template_id,
        filename,
        student_count,
        pdf_path,
        processed_data
    ))

    connection.commit()

    report_id = cursor.lastrowid

    connection.close()

    return report_id


# ============================================================
# GENERATED REPORTS — GET ALL
# ============================================================

def get_generated_reports(template_id=None):
    """
    Retrieve generated reports.

    If template_id is given, filter by that template.
    Otherwise return all reports.
    """

    connection = get_db_connection()

    if template_id:
        reports = connection.execute("""
            SELECT r.*, t.name as template_name,
                   t.school_name
            FROM generated_reports r
            JOIN report_templates t
                ON t.id = r.template_id
            WHERE r.template_id = ?
            ORDER BY r.created_at DESC
        """, (template_id,)).fetchall()
    else:
        reports = connection.execute("""
            SELECT r.*, t.name as template_name,
                   t.school_name
            FROM generated_reports r
            JOIN report_templates t
                ON t.id = r.template_id
            ORDER BY r.created_at DESC
            LIMIT 20
        """).fetchall()

    connection.close()

    return reports


# ============================================================
# DASHBOARD STATS
# ============================================================

def get_dashboard_stats():
    """
    Get summary statistics for the dashboard.
    """

    connection = get_db_connection()

    template_count = connection.execute(
        'SELECT COUNT(*) FROM report_templates'
    ).fetchone()[0]

    field_count = connection.execute(
        'SELECT COUNT(*) FROM report_fields'
    ).fetchone()[0]

    report_count = connection.execute(
        'SELECT COUNT(*) FROM generated_reports'
    ).fetchone()[0]

    recent_reports = connection.execute("""
        SELECT r.*, t.name as template_name,
               t.school_name
        FROM generated_reports r
        JOIN report_templates t
            ON t.id = r.template_id
        ORDER BY r.created_at DESC
        LIMIT 5
    """).fetchall()

    connection.close()

    return {
        'template_count': template_count,
        'field_count': field_count,
        'report_count': report_count,
        'recent_reports': recent_reports
    }


# ============================================================
# DEVELOPMENT TESTING
# ============================================================
#
# This section runs ONLY when we execute:
#
#     python database.py
#
# It does NOT run when app.py imports this module.
#

if __name__ == "__main__":

    # Create the database tables if they don't exist.
    initialize_database()

    print("Database initialized successfully.")

    # --------------------------------------------------------
    # CREATE TEST TEMPLATE
    # --------------------------------------------------------

    template_id = create_report_template(
        "ICRP Standard Report",
        "Netzah International School",
        "2026",
        "Term 1"
    )

    print("Created template:", template_id)


    # --------------------------------------------------------
    # ADD TEST FIELD 1
    # --------------------------------------------------------

    student_name_id = add_report_field(
        template_id,
        "Student Name",
        "NAME",
        "text",
        True,
        False,
        1
    )

    print("Created Student Name field:", student_name_id)


    # --------------------------------------------------------
    # ADD TEST FIELD 2
    # --------------------------------------------------------

    online_id = add_report_field(
        template_id,
        "Online Assessment",
        "ONLINE",
        "score",
        True,
        True,
        2
    )

    print("Created Online Assessment field:", online_id)


    # --------------------------------------------------------
    # ADD TEST FIELD 3
    # --------------------------------------------------------

    comment_id = add_report_field(
        template_id,
        "Teacher Comment",
        "COMMENT",
        "long_text",
        False,
        False,
        3
    )

    print("Created Teacher Comment field:", comment_id)


    # --------------------------------------------------------
    # DISPLAY TEMPLATE
    # --------------------------------------------------------

    template = get_report_template(template_id)

    print("\nTemplate:")
    print(dict(template))


    # --------------------------------------------------------
    # DISPLAY FIELDS
    # --------------------------------------------------------

    fields = get_report_fields(template_id)

    print("\nFields:")

    for field in fields:
        print(dict(field))