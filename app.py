from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
import os
from datetime import datetime
import mimetypes

# Import our database functions.
#
# database.py is responsible for:
# - Creating the SQLite database
# - Creating report templates
# - Creating report fields
# - Reading report templates
# - Reading report fields
# - Updating report fields
from database import (
    initialize_database,
    create_report_template,
    get_report_template,
    get_report_fields,
    add_report_field
)


# ============================================================
# FLASK APPLICATION
# ============================================================

mimetypes.add_type('text/css', '.css')

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# ============================================================
# APPLICATION FOLDERS
# ============================================================

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REPORTS_FOLDER'] = REPORTS_FOLDER


# Create the folders if they don't already exist.
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

# This makes sure the required database tables exist
# whenever the Flask application starts.
initialize_database()


# ============================================================
# OLD EXCEL COLUMN CONFIGURATION
# ============================================================

# IMPORTANT:
#
# This is still part of the OLD report-generation system.
#
# We will eventually replace this fixed list with the
# dynamically configured fields stored in SQLite.
#
# For now, we keep it so the existing report generator
# continues to work while we build the new system.

REQUIRED_COLUMNS = [
    'NAME',
    'REG NO',
    'GRADE',
    'COMMENT',
    'ONLINE ASSESSMENT',
    'PHYSICAL EXAM',
    'TOTAL'
]


# ============================================================
# HOME PAGE
# ============================================================

@app.route('/')
def index():

    # Display the SnapReport configuration screen.
    return render_template('index.html')


# ============================================================
# CREATE REPORT TEMPLATE
# ============================================================

@app.route('/create-report', methods=['POST'])
def create_report():

    """
    Creates a new report template in SQLite.

    The frontend sends:

        report_type
        school_name
        academic_year
        term

    Example:

        report_type = "ICRP Report"
        school_name = "Netzah International School"
        academic_year = "2026"
        term = "Term 1"

    SQLite then gives the template its own ID.

    Example:

        template_id = 5

    That ID will later identify the complete configuration
    for this particular report.
    """

    try:

        # ----------------------------------------------------
        # GET DATA FROM THE FRONTEND
        # ----------------------------------------------------

        report_type = request.form.get(
            'report_type',
            ''
        ).strip()

        school_name = request.form.get(
            'school_name',
            ''
        ).strip()

        academic_year = request.form.get(
            'academic_year',
            ''
        ).strip()

        term = request.form.get(
            'term',
            ''
        ).strip()


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not report_type:
            return jsonify({
                'error': 'Report type is required.'
            }), 400


        if not school_name:
            return jsonify({
                'error': 'School name is required.'
            }), 400


        if not academic_year:
            return jsonify({
                'error': 'Academic year is required.'
            }), 400


        if not term:
            return jsonify({
                'error': 'Academic term is required.'
            }), 400


        # ----------------------------------------------------
        # CREATE TEMPLATE
        # ----------------------------------------------------

        template_id = create_report_template(
            report_type,
            school_name,
            academic_year,
            term
        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({

            'success': True,

            'template_id': template_id,

            'message': 'Report configuration created successfully.'

        })


    except Exception as e:

        # Print the actual error in the terminal.
        print(
            f"Error creating report template: {e}"
        )

        return jsonify({
            'error': f'Unable to create report: {str(e)}'
        }), 500


# ============================================================
# REPORT CONFIGURATION PAGE
# ============================================================

@app.route('/configure/<int:template_id>')
def configure_report(template_id):

    """
    Displays the configuration page for a particular
    report template.

    Example:

        /configure/5

    means:

        "Open the configuration belonging to template 5."
    """

    # Retrieve the template from SQLite.
    template = get_report_template(template_id)


    # If the template doesn't exist, return a 404.
    if template is None:

        return (
            'Report template not found.',
            404
        )


    # Retrieve fields belonging to this template.
    fields = get_report_fields(template_id)


    # Send both the template and its fields to HTML.
    return render_template(
        'configure.html',
        template=template,
        fields=fields
    )
# ============================================================
# ADD REPORT FIELD
# ============================================================

@app.route('/api/report-fields', methods=['POST'])
def create_report_field():

    """
    Creates a new field for a report template.

    The browser sends the field information as JSON.

    Example:

    {
        "template_id": 8,
        "field_name": "Student Name",
        "excel_column": "NAME",
        "field_type": "text",
        "required": true,
        "include_in_grading": false,
        "display_order": 1
    }

    The information is then passed to database.py,
    which stores it in the report_fields table.
    """

    try:

        # Get JSON data sent by the browser.
        data = request.get_json()

        # ----------------------------------------------------
        # GET VALUES
        # ----------------------------------------------------

        template_id = data.get('template_id')

        field_name = data.get(
            'field_name',
            ''
        ).strip()

        excel_column = data.get(
            'excel_column',
            ''
        ).strip()

        field_type = data.get(
            'field_type',
            'text'
        )

        required = data.get(
            'required',
            False
        )

        include_in_grading = data.get(
            'include_in_grading',
            False
        )

        display_order = data.get(
            'display_order',
            0
        )


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not template_id:

            return jsonify({
                'error': 'Template ID is required.'
            }), 400


        if not field_name:

            return jsonify({
                'error': 'Field name is required.'
            }), 400


        if not excel_column:

            return jsonify({
                'error': 'Excel column is required.'
            }), 400


        # ----------------------------------------------------
        # MAKE SURE TEMPLATE EXISTS
        # ----------------------------------------------------

        template = get_report_template(
            template_id
        )


        if template is None:

            return jsonify({
                'error': 'Report template does not exist.'
            }), 404


        # ----------------------------------------------------
        # CREATE FIELD
        # ----------------------------------------------------

        field_id = add_report_field(

            template_id,

            field_name,

            excel_column,

            field_type,

            required,

            include_in_grading,

            display_order

        )


        # ----------------------------------------------------
        # RETURN RESULT
        # ----------------------------------------------------

        return jsonify({

            'success': True,

            'field_id': field_id,

            'message': 'Report field created successfully.'

        })


    except Exception as e:

        print(
            f"Error creating report field: {e}"
        )

        return jsonify({

            'error':
                f'Unable to create field: {str(e)}'

        }), 500

# ============================================================
# TEST IMAGE ROUTE
# ============================================================

@app.route('/test-image')
def test_image():

    return '<img src="/static/icrp_logo.png">'


# ============================================================
# OLD EXCEL UPLOAD ROUTE
# ============================================================

@app.route('/upload', methods=['POST'])
def upload():

    """
    OLD EXCEL UPLOAD SYSTEM.

    We are keeping this temporarily.

    Later this function will be modified so that it reads
    the user's dynamically configured fields from SQLite
    instead of using REQUIRED_COLUMNS.
    """

    if 'file' not in request.files:

        return jsonify({
            'error': 'No file uploaded'
        }), 400


    file = request.files['file']


    if file.filename == '':

        return jsonify({
            'error': 'No file selected'
        }), 400


    # Check that the uploaded file is an Excel file.
    if not (
        file.filename.endswith('.xlsx')
        or file.filename.endswith('.xls')
    ):

        return jsonify({
            'error': 'Only Excel files (.xlsx, .xls) are supported'
        }), 400


    # Save uploaded file.
    filepath = os.path.join(
        app.config['UPLOAD_FOLDER'],
        file.filename
    )

    file.save(filepath)


    try:

        # Read Excel file.
        df = pd.read_excel(filepath)


        # Normalize column names.
        df.columns = [
            str(c).strip().upper()
            for c in df.columns
        ]


        # ----------------------------------------------------
        # FLEXIBLE COLUMN MATCHING
        # ----------------------------------------------------

        col_map = {}


        for required in REQUIRED_COLUMNS:

            for actual in df.columns:

                if (
                    required in actual
                    or actual in required
                ):

                    col_map[required] = actual

                    break


        # Determine missing columns.
        missing = [
            c
            for c in REQUIRED_COLUMNS
            if c not in col_map
        ]


        if missing:

            return jsonify({
                'error':
                    f'Missing columns: '
                    f'{", ".join(missing)}. '
                    f'Found: '
                    f'{", ".join(df.columns.tolist())}'
            }), 400


        # Rename columns to our standard names.
        df = df.rename(
            columns={
                v: k
                for k, v in col_map.items()
            }
        )


        # Only keep valid student rows.
        df = df[
            REQUIRED_COLUMNS
        ].dropna(
            subset=[
                'NAME',
                'REG NO'
            ]
        )


        students = []


        # ----------------------------------------------------
        # BUILD STUDENT DATA
        # ----------------------------------------------------

        for _, row in df.iterrows():

            total = (
                float(row['TOTAL'])
                if pd.notna(row['TOTAL'])
                else 0
            )


            student = {

                'name':
                    str(
                        row['NAME']
                    ).strip(),

                'reg_no':
                    str(
                        row['REG NO']
                    ).strip(),

                'grade':
                    str(
                        row['GRADE']
                    ).strip(),

                'comment':
                    (
                        str(
                            row['COMMENT']
                        ).strip()
                        if pd.notna(
                            row['COMMENT']
                        )
                        else ''
                    ),

                'online_assessment':
                    (
                        float(
                            row['ONLINE ASSESSMENT']
                        )
                        if pd.notna(
                            row['ONLINE ASSESSMENT']
                        )
                        else 0
                    ),

                'physical_exam':
                    (
                        float(
                            row['PHYSICAL EXAM']
                        )
                        if pd.notna(
                            row['PHYSICAL EXAM']
                        )
                        else 0
                    ),

                'total':
                    total,

                'signature':
                    '/static/sign.png',

                'score':
                    get_score(total),

                'position':
                    0
            }


            students.append(student)


        # ----------------------------------------------------
        # RANK STUDENTS
        # ----------------------------------------------------

        students.sort(
            key=lambda x: x['total'],
            reverse=True
        )


        for i, student in enumerate(students):

            student['position'] = i + 1


        # ----------------------------------------------------
        # REPORT INFORMATION
        # ----------------------------------------------------

        school_name = request.form.get(
            'school_name',
            'Excellence Academy'
        )


        term = request.form.get(
            'term',
            'Term 1'
        )


        year = request.form.get(
            'year',
            str(datetime.now().year)
        )


        grade_level = (
            students[0]['grade']
            if students
            else 'N/A'
        )


        # ----------------------------------------------------
        # RETURN DATA
        # ----------------------------------------------------

        return jsonify({

            'success': True,

            'students': students,

            'meta': {

                'school_name':
                    school_name,

                'term':
                    term,

                'year':
                    year,

                'grade':
                    grade_level,

                'total_students':
                    len(students),

                'generated_at':
                    datetime.now().strftime(
                        '%B %d, %Y'
                    )
            }

        })


    except Exception as e:

        return jsonify({
            'error':
                f'Error reading file: {str(e)}'
        }), 500


# ============================================================
# GRADING FUNCTION
# ============================================================

def get_score(total):

    """
    OLD grading system.

    This will eventually become configurable.

    For example, instead of hard-coding:

        90 -> A+
        80 -> A
        70 -> B

    the user will eventually be able to configure:

        A+ = 90-100
        A  = 80-89
        B  = 70-79

    and even create completely different grading systems.
    """

    if total >= 90:
        return ('A+', 'SuperB')


    if total >= 80:
        return ('A', 'Excellent')


    if total >= 70:
        return ('B', 'Very Good')


    if total >= 60:
        return ('C', 'Good')


    if total >= 40:
        return ('D', 'Average')


    return ('F', 'Below Average')


# ============================================================
# OLD REPORT PAGE
# ============================================================

@app.route('/report')
def report_page():

    return render_template(
        'report.html'
    )


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == '__main__':

    app.run(
        debug=True,
        port=5000
    )