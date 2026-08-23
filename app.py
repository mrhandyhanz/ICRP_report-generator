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
    get_db_connection,
    create_report_template,
    get_report_template,
    add_report_field,
    get_report_fields,
    get_report_field,
    update_report_field,
    delete_report_field,
    get_all_templates,
    delete_report_template,
    get_grade_boundaries,
    save_grade_boundaries,
    apply_grading,
    create_generated_report,
    get_generated_reports,
    get_dashboard_stats
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
# TEMPLATES LIST PAGE
# ============================================================

@app.route('/templates')
def templates_list():

    # Get every template with its field count.
    templates = get_all_templates()

    return render_template(
        'templates.html',
        templates=templates
    )
    
# ============================================================
# DELETE REPORT TEMPLATE
# ============================================================

@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
def api_delete_template(template_id):
    """
    Delete a report template and all its fields.
    """

    try:

        # Check that the template exists.
        template = get_report_template(template_id)

        if template is None:
            return jsonify({
                'error': 'Template not found.'
            }), 404

        # Delete it (and its fields via CASCADE).
        delete_report_template(template_id)

        return jsonify({
            'success': True,
            'message': 'Template deleted successfully.'
        })

    except Exception as e:

        print("Error deleting template:", e)

        return jsonify({
            'error': str(e)
        }), 500
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

    return '<img src="/static/snapreport_logo.png">'


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


    # Check that the uploaded file is an Excel or CSV file.
    if not (
        file.filename.endswith('.xlsx')
        or file.filename.endswith('.xls')
        or file.filename.endswith('.csv')
    ):

        return jsonify({
            'error': 'Only Excel (.xlsx, .xls) and CSV (.csv) files are supported'
        }), 400


    # Save uploaded file.
    filepath = os.path.join(
        app.config['UPLOAD_FOLDER'],
        file.filename
    )

    file.save(filepath)


    try:

        # Read Excel or CSV file.
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
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
# DASHBOARD
# ============================================================

@app.route('/dashboard')
def dashboard():

    stats = get_dashboard_stats()

    return render_template(
        'dashboard.html',
        stats=stats
    )


# ============================================================
# GRADING PAGE
# ============================================================

@app.route('/configure/<int:template_id>/grading')
def grading_page(template_id):

    template = get_report_template(template_id)

    if template is None:
        return ('Template not found.', 404)

    boundaries = get_grade_boundaries(template_id)

    return render_template(
        'grading.html',
        template=template,
        boundaries=boundaries
    )


# ============================================================
# GRADE BOUNDARIES API
# ============================================================

@app.route(
    '/api/templates/<int:template_id>/grade-boundaries',
    methods=['POST']
)
def api_save_grade_boundaries(template_id):

    try:

        template = get_report_template(template_id)

        if template is None:
            return jsonify({
                'error': 'Template not found.'
            }), 404

        data = request.get_json()

        boundaries = data.get('boundaries', [])

        # Validate each boundary.
        for b in boundaries:
            if 'min_score' not in b or 'max_score' not in b:
                return jsonify({
                    'error': 'Each boundary needs min_score and max_score.'
                }), 400
            if 'grade' not in b:
                return jsonify({
                    'error': 'Each boundary needs a grade label.'
                }), 400

        save_grade_boundaries(template_id, boundaries)

        return jsonify({
            'success': True,
            'message': 'Grade boundaries saved.'
        })

    except Exception as e:

        print('Error saving grade boundaries:', e)

        return jsonify({
            'error': str(e)
        }), 500


# ============================================================
# UPLOAD & PROCESS EXCEL
# ============================================================

@app.route('/configure/<int:template_id>/upload')
def upload_page(template_id):

    template = get_report_template(template_id)

    if template is None:
        return ('Template not found.', 404)

    fields = get_report_fields(template_id)

    return render_template(
        'upload.html',
        template=template,
        fields=fields
    )


@app.route(
    '/api/templates/<int:template_id>/upload',
    methods=['POST']
)
def api_upload_excel(template_id):

    """
    Upload an Excel file, validate it against
    the template's fields, and return processed data.
    """

    try:

        template = get_report_template(template_id)

        if template is None:
            return jsonify({
                'error': 'Template not found.'
            }), 404

        # Get the uploaded file.
        if 'file' not in request.files:
            return jsonify({
                'error': 'No file uploaded.'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'error': 'No file selected.'
            }), 400

        # Check file extension.
        if not (
            file.filename.endswith('.xlsx')
            or file.filename.endswith('.xls')
            or file.filename.endswith('.csv')
        ):
            return jsonify({
                'error': 'Only .xlsx, .xls, and .csv files are supported.'
            }), 400

        # Save the file.
        filepath = os.path.join(
            app.config['UPLOAD_FOLDER'],
            file.filename
        )

        file.save(filepath)

        # Get the template's configured fields.
        fields = get_report_fields(template_id)

        if not fields:
            return jsonify({
                'error': 'No fields configured. Add fields before uploading.'
            }), 400

        # Read the Excel or CSV file.
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath)
        else:
            df = pd.read_excel(filepath)

        # Normalize column names.
        df.columns = [
            str(c).strip().upper()
            for c in df.columns
        ]

        # ----------------------------------------------------
        # VALIDATE COLUMNS
        # ----------------------------------------------------

        expected_columns = [
            f['excel_column'].upper()
            for f in fields
        ]

        # Flexible column matching.
        col_map = {}
        missing_columns = []

        for expected in expected_columns:
            found = False
            for actual in df.columns:
                if (
                    expected in actual
                    or actual in expected
                ):
                    col_map[expected] = actual
                    found = True
                    break
            if not found:
                missing_columns.append(expected)

        if missing_columns:
            return jsonify({
                'error': f'Missing columns: {chr(10).join(missing_columns)}. Found: {chr(10).join(df.columns.tolist())}',
                'missing_columns': missing_columns,
                'found_columns': df.columns.tolist()
            }), 400

        # Rename to our standard names.
        df = df.rename(
            columns={v: k for k, v in col_map.items()}
        )

        # ----------------------------------------------------
        # VALIDATE REQUIRED FIELDS
        # ----------------------------------------------------

        required_fields = [
            f['excel_column'].upper()
            for f in fields
            if f['required']
        ]

        # Find the first text-like field as the "name" column
        # for identifying students in error messages.
        name_column = None
        for f in fields:
            if f['field_type'] in ('text', 'long_text'):
                name_column = f['excel_column'].upper()
                break

        validation_errors = []

        for idx, row in df.iterrows():
            for col in required_fields:
                if pd.isna(row.get(col)) or str(row.get(col)).strip() == '':
                    student_id = (
                        str(row.get(name_column, f'Row {idx + 2}'))
                        if name_column
                        else f'Row {idx + 2}'
                    )
                    validation_errors.append(
                        f'{student_id}: Missing required value in "{col}"'
                    )

            # Check for duplicate records.
            if name_column:
                name_val = str(row.get(name_column, '')).strip()
                if name_val:
                    dupes = df[
                        df[name_column].astype(str).str.strip().str.upper()
                        == name_val.upper()
                    ]
                    if len(dupes) > 1 and idx == dupes.index[0]:
                        # Only flag the first occurrence.
                        pass
                    elif len(dupes) > 1 and idx != dupes.index[0]:
                        validation_errors.append(
                            f'{name_val}: Duplicate record'
                        )

        if validation_errors:
            return jsonify({
                'error': f'{len(validation_errors)} validation error(s) found.',
                'validation_errors': validation_errors[:50]
            }), 400

        # ----------------------------------------------------
        # PROCESS RECORDS
        # ----------------------------------------------------

        students = []

        for _, row in df.iterrows():
            student = {}

            for field in fields:
                col = field['excel_column'].upper()
                value = row.get(col)

                # Convert based on field type.
                if field['field_type'] == 'score':
                    student[field['field_name']] = (
                        float(value) if pd.notna(value) else 0
                    )
                elif field['field_type'] == 'number':
                    student[field['field_name']] = (
                        float(value) if pd.notna(value) else 0
                    )
                else:
                    student[field['field_name']] = (
                        str(value).strip()
                        if pd.notna(value)
                        else ''
                    )

            students.append(student)

        # ----------------------------------------------------
        # CALCULATE TOTALS & APPLY GRADING
        # ----------------------------------------------------

        # Sum all score-type fields for each student.
        score_fields = [
            f['field_name']
            for f in fields
            if f['field_type'] == 'score'
            and f['include_in_grading']
        ]

        for student in students:
            total = sum(
                student.get(sf, 0)
                for sf in score_fields
            )

            student['_total'] = total

            grade, remark = apply_grading(
                template_id,
                total
            )

            student['_grade'] = grade
            student['_remark'] = remark

        # Sort by total descending.
        students.sort(
            key=lambda x: x.get('_total', 0),
            reverse=True
        )

        # Add position.
        for i, student in enumerate(students):
            student['_position'] = i + 1

        # ----------------------------------------------------
        # SAVE REPORT RECORD
        # ----------------------------------------------------

        import json

        report_id = create_generated_report(
            template_id,
            file.filename,
            len(students),
            processed_data=json.dumps(students)
        )

        # ----------------------------------------------------
        # RETURN DATA
        # ----------------------------------------------------

        return jsonify({
            'success': True,
            'report_id': report_id,
            'students': students,
            'meta': {
                'school_name': template['school_name'],
                'term': template['term'],
                'year': template['academic_year'],
                'template_name': template['name'],
                'total_students': len(students),
                'score_fields': score_fields,
                'generated_at': datetime.now().strftime(
                    '%B %d, %Y'
                )
            }
        })

    except Exception as e:

        print('Error processing Excel:', e)

        return jsonify({
            'error': f'Error processing file: {str(e)}'
        }), 500


# ============================================================
# REPORTS LIST PAGE
# ============================================================

@app.route('/reports')
def reports_list():

    reports = get_generated_reports()

    return render_template(
        'reports.html',
        reports=reports
    )


@app.route('/reports/<int:template_id>')
def reports_for_template(template_id):

    template = get_report_template(template_id)

    if template is None:
        return ('Template not found.', 404)

    reports = get_generated_reports(template_id)

    return render_template(
        'reports.html',
        template=template,
        reports=reports
    )


# ============================================================
# DOWNLOAD REPORT PDF
# ============================================================

@app.route('/api/reports/<int:report_id>/download')
def download_report(report_id):
    """
    Generate and download a PDF report with per-student report cards.

    Each student gets their own page matching the report.html viewer format:
    - School header with name, term, year
    - Student info section (2-column grid)
    - Score boxes for each score field + total
    - Grade pill with remark
    - Comment section (if any)
    - Signature footer
    """

    try:
        import json

        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle,
            Paragraph, Spacer, PageBreak, HRFlowable, Image
        )
        from reportlab.lib.styles import (
            getSampleStyleSheet, ParagraphStyle
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        connection = get_db_connection()

        report = connection.execute("""
            SELECT r.*, t.name as template_name,
                   t.school_name, t.academic_year, t.term
            FROM generated_reports r
            JOIN report_templates t ON t.id = r.template_id
            WHERE r.id = ?
        """, (report_id,)).fetchone()

        connection.close()

        if report is None:
            return jsonify({
                'error': 'Report not found.'
            }), 404

        # Get the template's fields.
        fields = get_report_fields(report['template_id'])

        # Parse stored student data.
        students = []
        if report['processed_data']:
            students = json.loads(report['processed_data'])

        # ---- Classify fields ----
        score_field_names = [
            f['field_name'] for f in fields
            if f['field_type'] == 'score' and f['include_in_grading']
        ]
        info_fields = [
            f for f in fields
            if f['field_type'] not in ('score',)
        ]
        comment_fields = [
            f for f in info_fields
            if f['field_type'] == 'long_text'
            or 'comment' in f['field_name'].lower()
            or 'remark' in f['field_name'].lower()
            or 'note' in f['field_name'].lower()
        ]
        name_field = None
        for f in fields:
            if f['field_type'] in ('text', 'long_text'):
                name_field = f['field_name']
                break
        if name_field is None and info_fields:
            name_field = info_fields[0]['field_name']

        # Build the PDF.
        pdf_filename = f"report_{report_id}.pdf"
        pdf_path = os.path.join(
            app.config['REPORTS_FOLDER'],
            pdf_filename
        )

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=18*mm,
            leftMargin=18*mm,
            topMargin=15*mm,
            bottomMargin=15*mm
        )

        styles = getSampleStyleSheet()
        page_width = A4[0] - 36*mm  # usable width

        # ---- Custom Styles ----
        school_name_style = ParagraphStyle(
            'SchoolName',
            parent=styles['Title'],
            fontSize=20,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0D1B2A'),
            spaceAfter=2*mm
        )
        school_sub_style = ParagraphStyle(
            'SchoolSub',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=4*mm
        )
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2563EB'),
            spaceAfter=3*mm
        )
        label_style = ParagraphStyle(
            'Label',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#94A3B8'),
        )
        value_style = ParagraphStyle(
            'Value',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0D1B2A'),
        )
        score_label_style = ParagraphStyle(
            'ScoreLabel',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#64748B'),
            alignment=TA_CENTER
        )
        score_value_style = ParagraphStyle(
            'ScoreValue',
            parent=styles['Normal'],
            fontSize=18,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        )
        score_sub_style = ParagraphStyle(
            'ScoreSub',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#94A3B8'),
            alignment=TA_CENTER
        )
        grade_style = ParagraphStyle(
            'Grade',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
        )
        comment_style = ParagraphStyle(
            'Comment',
            parent=styles['Normal'],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#475569'),
        )
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#94A3B8'),
            alignment=TA_RIGHT
        )
        sig_label_style = ParagraphStyle(
            'SigLabel',
            parent=styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#94A3B8'),
            alignment=TA_CENTER
        )

        # ---- Build per-student report cards ----
        elements = []
        navy = colors.HexColor('#0D1B2A')
        blue = colors.HexColor('#2563EB')
        insight = colors.HexColor('#14B8A6')
        border_color = colors.HexColor('#E2E8F0')
        green = colors.HexColor('#16A34A')
        red = colors.HexColor('#DC2626')

        for idx, student in enumerate(students):
            if idx > 0:
                elements.append(PageBreak())

            total = student.get('_total', 0)
            grade = str(student.get('_grade', ''))
            remark = str(student.get('_remark', ''))
            pct = min(100, round(total))

            # ---- Accent bar (thin colored line at top) ----
            elements.append(HRFlowable(
                width='100%', thickness=3,
                color=blue, spaceAfter=3*mm
            ))

            # ---- School Header (matching HTML format) ----
            logo_path = os.path.join(
                BASE_DIR, 'static', 'icrp_logo.png'
            )
            netzah_path = os.path.join(
                BASE_DIR, 'static', 'netzah.jpeg'
            )
            sign_path = os.path.join(
                BASE_DIR, 'static', 'sign.png'
            )

            # Header table: school info left, logos right
            header_left = [
                Paragraph(
                    str(report['school_name']),
                    school_name_style
                ),
                Paragraph(
                    f"{report['term']} {report['academic_year']}"
                    f" &nbsp;|&nbsp; {report['template_name']}",
                    school_sub_style
                )
            ]
            header_left_table = Table(
                [[header_left]],
                colWidths=[page_width * 0.6]
            )
            header_left_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))

            # Right side: both logos
            logo_elements = []
            if os.path.exists(logo_path):
                logo_elements.append(
                    Image(logo_path, width=30*mm, height=15*mm)
                )
            if os.path.exists(netzah_path):
                logo_elements.append(
                    Image(netzah_path, width=15*mm, height=15*mm)
                )

            header_right_table = Table(
                [[logo_elements]],
                colWidths=[page_width * 0.4]
            )
            header_right_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))

            header_table = Table(
                [[header_left_table, header_right_table]],
                colWidths=[page_width * 0.6, page_width * 0.4]
            )
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))

            elements.append(header_table)
            elements.append(HRFlowable(
                width='100%', thickness=0.5,
                color=border_color, spaceAfter=4*mm, spaceBefore=2*mm
            ))

            # ---- Student Info (2-column table) ----
            left_info = []
            right_info = []
            for i, f in enumerate(info_fields):
                val = str(student.get(f['field_name'], ''))
                row = [
                    Paragraph(f['field_name'].upper(), label_style),
                    Paragraph(val, value_style)
                ]
                if i % 2 == 0:
                    left_info.append(row)
                else:
                    right_info.append(row)

            # Add grade + year to right column
            right_info.append([
                Paragraph('GRADE', label_style),
                Paragraph(grade, value_style)
            ])
            right_info.append([
                Paragraph('ACADEMIC YEAR', label_style),
                Paragraph(str(report['academic_year']), value_style)
            ])

            # Pad shorter column
            while len(left_info) < len(right_info):
                left_info.append(['', ''])
            while len(right_info) < len(left_info):
                right_info.append(['', ''])

            left_table = Table(
                left_info,
                colWidths=[28*mm, page_width/2 - 30*mm]
            )
            left_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
            ]))

            right_table = Table(
                right_info,
                colWidths=[28*mm, page_width/2 - 30*mm]
            )
            right_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
            ]))

            info_table = Table(
                [[left_table, right_table]],
                colWidths=[page_width/2, page_width/2]
            )
            info_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
                ('LINEBEFORE', (1, 0), (1, -1), 0.5, border_color),
                ('LEFTPADDING', (1, 0), (1, -1), 4*mm),
            ]))

            elements.append(info_table)
            elements.append(HRFlowable(
                width='100%', thickness=0.5,
                color=border_color, spaceAfter=4*mm, spaceBefore=2*mm
            ))

            # ---- Scores Section ----
            if score_field_names:
                elements.append(Paragraph(
                    'PERFORMANCE SUMMARY',
                    section_title_style
                ))

                # Build score boxes as a horizontal table
                score_cells = []
                label_cells = []
                sub_cells = []

                for sf in score_field_names:
                    label_cells.append(
                        Paragraph(sf.upper(), score_label_style)
                    )
                    score_cells.append(
                        Paragraph(str(student.get(sf, 0)), score_value_style)
                    )
                    sub_cells.append(
                        Paragraph('marks', score_sub_style)
                    )

                # Add total
                label_cells.append(
                    Paragraph('TOTAL SCORE', score_label_style)
                )
                score_cells.append(
                    Paragraph(str(total), ParagraphStyle(
                        'TotalVal', parent=score_value_style,
                        textColor=blue
                    ))
                )
                sub_cells.append(
                    Paragraph(f'out of {len(score_field_names)}00', score_sub_style)
                )

                num_scores = len(score_field_names) + 1
                col_w = page_width / num_scores

                score_table = Table(
                    [label_cells, score_cells, sub_cells],
                    colWidths=[col_w] * num_scores
                )
                score_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                    ('BOX', (0, 0), (num_scores-2, -1), 0.5, border_color),
                    ('BOX', (num_scores-1, 0), (num_scores-1, -1), 0.5, blue),
                    ('ROUNDEDCORNERS', [2, 2, 2, 2]),
                ]))

                elements.append(score_table)
                elements.append(Spacer(1, 3*mm))

                # Grade pill + progress bar
                grade_color = green if grade.upper().startswith(('A', 'B')) else (
                    red if grade.upper().startswith('F') else colors.HexColor('#F59E0B')
                )
                grade_table = Table(
                    [[
                        Paragraph(
                            f"<b>{grade}</b> &mdash; {remark}",
                            ParagraphStyle(
                                'GradePill',
                                parent=styles['Normal'],
                                fontSize=10,
                                textColor=grade_color
                            )
                        )
                    ]],
                    colWidths=[page_width]
                )
                grade_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1),
                        colors.HexColor('#F8FAFC')),
                    ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3*mm),
                    ('BOX', (0, 0), (-1, -1), 0.5, border_color),
                ]))
                elements.append(grade_table)

                # Progress bar (simple table with fill)
                elements.append(Spacer(1, 3*mm))
                bar_filled = max(1, round(page_width * pct / 100))
                bar_empty = max(0, page_width - bar_filled)
                progress_table = Table(
                    [['']],
                    colWidths=[bar_filled, bar_empty]
                )
                progress_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, 0), blue),
                    ('BACKGROUND', (1, 0), (1, 0), border_color),
                    ('TOPPADDING', (0, 0), (-1, -1), 1),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ]))
                elements.append(progress_table)
                elements.append(HRFlowable(
                    width='100%', thickness=0.5,
                    color=border_color, spaceAfter=4*mm, spaceBefore=4*mm
                ))

            # ---- Comment Section ----
            for cf in comment_fields:
                val = str(student.get(cf['field_name'], '')).strip()
                if val:
                    elements.append(Paragraph(
                        cf['field_name'].upper(),
                        section_title_style
                    ))
                    comment_table = Table(
                        [[Paragraph(val, comment_style)]],
                        colWidths=[page_width]
                    )
                    comment_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1),
                            colors.HexColor('#F8FAFC')),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4*mm),
                        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
                        ('LINEBEFOREDECOR', (0, 0), (0, -1), 2, blue),
                        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
                    ]))
                    elements.append(comment_table)
                    elements.append(HRFlowable(
                        width='100%', thickness=0.5,
                        color=border_color, spaceAfter=4*mm, spaceBefore=4*mm
                    ))

            # ---- Footer (signature image + stamp, matching HTML) ----
            # Left: signature image with underline + label
            sig_elements = []
            if os.path.exists(sign_path):
                sig_elements.append(
                    Image(sign_path, width=35*mm, height=15*mm)
                )
            else:
                sig_elements.append(
                    Paragraph('___________________', sig_label_style)
                )
            sig_elements.append(
                Paragraph('TECHNICAL REPRESENTATIVE', sig_label_style)
            )

            sig_col = Table(
                [[e] for e in sig_elements],
                colWidths=[page_width * 0.35]
            )
            sig_col.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('LINEBELOW', (0, 0), (0, 0), 1, colors.HexColor('#0D1B2A')),
            ]))

            stamp_col = Table(
                [[Paragraph(
                    f"{report['school_name']}<br/>{report['term']} {report['academic_year']}",
                    footer_style
                )]],
                colWidths=[page_width * 0.35]
            )
            stamp_col.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ]))

            footer_table = Table(
                [[sig_col, '', stamp_col]],
                colWidths=[page_width*0.35, page_width*0.3, page_width*0.35]
            )
            footer_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(Spacer(1, 6*mm))
            elements.append(footer_table)

        doc.build(elements)

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=pdf_filename
        )

    except ImportError:

        return jsonify({
            'error': 'PDF generation requires reportlab. Install with: pip install reportlab'
        }), 500

    except Exception as e:

        print('Error generating PDF:', e)

        return jsonify({
            'error': f'Error generating PDF: {str(e)}'
        }), 500


# ============================================================
# OLD REPORT PAGE
# ============================================================

@app.route('/report')
def report_page():

    return render_template(
        'report.html'
    )


@app.route('/api/report-fields/<int:field_id>', methods=['GET'])
def api_get_report_field(field_id):
    """
    Return one report field as JSON.
    """

    try:
        field = get_report_field(field_id)

        if field is None:
            return jsonify({
                'error': 'Report field not found.'
            }), 404

        return jsonify({
            'success': True,
            'field': dict(field)
        })

    except Exception as e:

        print("Error getting report field:", e)

        return jsonify({
            'error': str(e)
        }), 500
@app.route('/api/report-fields/<int:field_id>', methods=['PUT'])
def api_update_report_field(field_id):
    """
    Update an existing report field.
    """

    try:

        # Check that the field actually exists.
        existing_field = get_report_field(field_id)

        if existing_field is None:
            return jsonify({
                'error': 'Report field not found.'
            }), 404

        # Get JSON sent by the browser.
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'No field data received.'
            }), 400

        # Extract values.
        field_name = data.get('field_name', '').strip()
        excel_column = data.get('excel_column', '').strip()
        field_type = data.get('field_type', 'text')
        required = data.get('required', False)
        include_in_grading = data.get(
            'include_in_grading',
            False
        )
        display_order = data.get('display_order', 1)

        # Basic validation.
        if not field_name:
            return jsonify({
                'error': 'Field name is required.'
            }), 400

        if not excel_column:
            return jsonify({
                'error': 'Excel column is required.'
            }), 400

        # Update the database.
        update_report_field(
            field_id,
            field_name,
            excel_column,
            field_type,
            required,
            include_in_grading,
            display_order
        )

        return jsonify({
            'success': True,
            'message': 'Report field updated successfully.'
        })

    except Exception as e:

        print("Error updating report field:", e)

        return jsonify({
            'error': str(e)
        }), 500
@app.route('/api/report-fields/<int:field_id>', methods=['DELETE'])
def api_delete_report_field(field_id):
    """
    Delete an existing report field.
    """

    try:

        # Check that the field exists.
        existing_field = get_report_field(field_id)

        if existing_field is None:
            return jsonify({
                'error': 'Report field not found.'
            }), 404

        # Delete it.
        delete_report_field(field_id)

        return jsonify({
            'success': True,
            'message': 'Report field deleted successfully.'
        })

    except Exception as e:

        print("Error deleting report field:", e)

        return jsonify({
            'error': str(e)
        }), 500


# ============================================================
# APPLICATION START
# ============================================================

if __name__ == '__main__':

    app.run(
        debug=True,
        port=5000
    )
