# ============================================================
# DATABASE MODULE
# ICRP Report Generator
# ============================================================

# sqlite3 is Python's built-in library for working with
# SQLite databases.
import sqlite3

# Path helps us create file paths in a reliable way.
from pathlib import Path


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

# Get the directory where this database.py file is located.
#
# This means our database will stay inside the project folder,
# regardless of where we run the application from.
BASE_DIR = Path(__file__).resolve().parent


# Name and location of our SQLite database.
#
# This creates:
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

    Other parts of our application will call this function
    whenever they need to read from or write to the database.
    """

    # Open the SQLite database.
    connection = sqlite3.connect(DATABASE)

    # Normally SQLite returns rows as tuples.
    #
    # sqlite3.Row allows us to access database values using
    # column names.
    #
    # Example:
    #
    # template["name"]
    #
    # instead of:
    #
    # template[1]
    connection.row_factory = sqlite3.Row

    # Enable SQLite foreign-key enforcement.
    #
    # This is important because report_fields is connected
    # to report_templates using a foreign key.
    connection.execute("PRAGMA foreign_keys = ON")

    # Return the connection to the function that requested it.
    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():
    """
    Create the tables required by the application.

    CREATE TABLE IF NOT EXISTS means that the table will only
    be created if it does not already exist.

    Therefore, running this function again will not erase
    existing data.
    """

    # Open a connection to the database.
    connection = get_db_connection()


    # ========================================================
    # REPORT TEMPLATES TABLE
    # ========================================================
    #
    # This table stores the general information about a report.
    #
    # Example:
    #
    # Name:          ICRP Standard Report
    # School:        Netzah International School
    # Academic Year: 2026
    # Term:          Term 1
    #

    connection.execute("""
        CREATE TABLE IF NOT EXISTS report_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Name given to the report template.
            name TEXT NOT NULL,

            -- School or organization using the report.
            school_name TEXT,

            -- Academic year of the report.
            academic_year TEXT,

            -- Term or semester being reported.
            term TEXT,

            -- Automatically records when the template was created.
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # ========================================================
    # REPORT FIELDS TABLE
    # ========================================================
    #
    # This table stores the individual fields that belong
    # to each report template.
    #
    # Example fields:
    #
    # Student Name
    # Registration Number
    # Online Assessment
    # Physical Assessment
    # Attendance
    # Teacher Comment
    #

    connection.execute("""
        CREATE TABLE IF NOT EXISTS report_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            template_id INTEGER NOT NULL,

            field_name TEXT NOT NULL,

            excel_column TEXT NOT NULL,

            field_type TEXT NOT NULL DEFAULT 'text',

            required INTEGER NOT NULL DEFAULT 0,

            include_in_grading INTEGER NOT NULL DEFAULT 0,

            display_order INTEGER NOT NULL DEFAULT 0,

            FOREIGN KEY (template_id)
                REFERENCES report_templates(id)
                ON DELETE CASCADE
        )
    """)


    # Save all database changes.
    connection.commit()

    # Close the connection because we are finished with it.
    connection.close()


# ============================================================
# CREATE REPORT TEMPLATE
# ============================================================

def create_report_template(name, school_name, academic_year, term):
    """
    Create a new report template.

    Example:

        create_report_template(
            "ICRP Standard Report",
            "Netzah International School",
            "2026",
            "Term 1"
        )
    """

    # Connect to the database.
    connection = get_db_connection()

    # Insert the new template into the report_templates table.
    #
    # The ? symbols are parameterized SQL placeholders.
    # This is safer than inserting values directly into SQL.
    cursor = connection.execute("""
        INSERT INTO report_templates
        (name, school_name, academic_year, term)
        VALUES (?, ?, ?, ?)
    """, (
        name,
        school_name,
        academic_year,
        term
    ))

    # Save the new record.
    connection.commit()

    # SQLite automatically creates an ID for the new template.
    #
    # cursor.lastrowid gives us that ID.
    template_id = cursor.lastrowid

    # Close the database connection.
    connection.close()

    # Return the newly created template ID.
    return template_id


# ============================================================
# GET ONE REPORT TEMPLATE
# ============================================================

def get_report_template(template_id):
    """
    Retrieve one report template using its ID.

    Example:

        get_report_template(1)

    retrieves the template whose ID is 1.
    """

    # Connect to the database.
    connection = get_db_connection()

    # Search for the requested template.
    template = connection.execute("""
        SELECT *
        FROM report_templates
        WHERE id = ?
    """, (template_id,)).fetchone()

    # Close the connection.
    connection.close()

    # Return the template.
    return template


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

    This will eventually power the [+ Add Field] button
    in our web interface.
    """

    # Connect to the database.
    connection = get_db_connection()

    # Insert the new field.
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

        # SQLite stores Boolean values as 0 or 1.
        # False becomes 0 and True becomes 1.
        int(required),

        # Same conversion for grading participation.
        int(include_in_grading),

        display_order
    ))

    # Save the new field.
    connection.commit()

    # Get the ID automatically generated for this field.
    field_id = cursor.lastrowid

    # Close the connection.
    connection.close()

    # Return the new field ID.
    return field_id


# ============================================================
# GET REPORT FIELDS
# ============================================================

def get_report_fields(template_id):
    """
    Retrieve all fields belonging to a specific report template.

    The fields are returned according to their display_order.
    """

    # Connect to the database.
    connection = get_db_connection()

    # Retrieve all fields belonging to this template.
    fields = connection.execute("""
        SELECT *
        FROM report_fields
        WHERE template_id = ?
        ORDER BY display_order ASC, id ASC
    """, (template_id,)).fetchall()

    # Close the connection.
    connection.close()

    # Return the fields.
    return fields


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

    This will eventually power an [Edit] button in the
    report configuration interface.
    """

    # Connect to the database.
    connection = get_db_connection()

    # Update the field whose ID matches field_id.
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

        # Convert True/False to SQLite's 1/0.
        int(required),

        # Convert True/False to SQLite's 1/0.
        int(include_in_grading),

        display_order,

        # Identify the field that should be updated.
        field_id
    ))

    # Save the changes.
    connection.commit()

    # Close the connection.
    connection.close()


# ============================================================
# DELETE REPORT FIELD
# ============================================================

def delete_report_field(field_id):
    """
    Delete one field from a report template.

    This will eventually power the [Delete] button in the
    report configuration interface.
    """

    # Connect to the database.
    connection = get_db_connection()

    # Delete the field whose ID matches field_id.
    connection.execute("""
        DELETE FROM report_fields
        WHERE id = ?
    """, (field_id,))

    # Save the deletion.
    connection.commit()

    # Close the connection.
    connection.close()


# ============================================================
# TEMPORARY DEVELOPMENT TEST
# ============================================================
#
# This section is ONLY for testing our database functions
# while we are developing.
#
# Later, we will remove this section and the Flask application
# will use the functions above.
#
# This code runs only when we execute:
#
#     python database.py
#
# It does NOT run when app.py imports database.py.
#

if __name__ == "__main__":

    # Make sure the database tables exist.
    initialize_database()

    print("Database initialized successfully.")

    # --------------------------------------------------------
    # CREATE A TEST REPORT TEMPLATE
    # --------------------------------------------------------

    template_id = create_report_template(
        "ICRP Standard Report",
        "Netzah International School",
        "2026",
        "Term 1"
    )

    print("Created template:", template_id)


    # --------------------------------------------------------
    # ADD TEST FIELDS
    # --------------------------------------------------------

    # Student Name:
    # - Text field
    # - Required
    # - Does not participate in grading
    # - Appears first
    add_report_field(
        template_id,
        "Student Name",
        "NAME",
        "text",
        True,
        False,
        1
    )


    # Online Assessment:
    # - Score field
    # - Required
    # - Participates in grading
    # - Appears second
    add_report_field(
        template_id,
        "Online Assessment",
        "ONLINE",
        "score",
        True,
        True,
        2
    )


    # Teacher Comment:
    # - Long text field
    # - Not required
    # - Does not participate in grading
    # - Appears third
    add_report_field(
        template_id,
        "Teacher Comment",
        "COMMENT",
        "long_text",
        False,
        False,
        3
    )


    # --------------------------------------------------------
    # RETRIEVE THE TEMPLATE
    # --------------------------------------------------------

    template = get_report_template(template_id)

    print("\nTemplate:")
    print(dict(template))


    # --------------------------------------------------------
    # RETRIEVE THE FIELDS
    # --------------------------------------------------------

    fields = get_report_fields(template_id)

    print("\nFields:")

    for field in fields:
        print(dict(field))