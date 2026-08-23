/* =========================================================
   SNAPREPORT — CONFIGURE PAGE
   JavaScript for report field management
   ========================================================= */


/* =========================================================
   GET TEMPLATE ID
   =========================================================

   The HTML page gives us the template ID through:

       <body data-template-id="8">

   JavaScript then reads that value.
   ========================================================= */

const templateId =
    document.body.dataset.templateId;


/* =========================================================
   OPEN ADD FIELD MODAL
   ========================================================= */

function openAddField() {

    const modal =
        document.getElementById('fieldModal');

    modal.classList.add('active');
}


/* =========================================================
   CLOSE FIELD MODAL
   ========================================================= */

function closeFieldModal() {

    const modal =
        document.getElementById('fieldModal');

    modal.classList.remove('active');


    /*
        Reset the form so that when the user opens
        the modal again, the previous values are gone.
    */

    const form =
        document.getElementById('fieldForm');

    form.reset();


    /*
        Reset display order because form.reset()
        returns it to its original HTML value.
    */

    document.getElementById('displayOrder').value = 1;

    /*
        Clear the hidden field ID so the save
        handler knows we are back in "add" mode.
    */

    document.getElementById('fieldId').value = '';

    /*
        Restore the modal heading to "Add" mode.
    */        const modalTitle =
            document.getElementById('modalTitle');

        if (modalTitle) {
            modalTitle.textContent =
                'Add Report Field';
        }
}


/* =========================================================
   SAVE NEW FIELD
   ========================================================= */

document
    .getElementById('fieldForm')
    .addEventListener(
        'submit',
        async function(event) {

            /*
                Prevent normal browser form submission.

                Without this:

                    browser → page reload

                With this:

                    JavaScript → Flask API
            */

            event.preventDefault();


            /* ------------------------------------------------
               COLLECT FIELD NAME
               ------------------------------------------------ */

            const fieldName =
                document
                    .getElementById('fieldName')
                    .value
                    .trim();


            /* ------------------------------------------------
               COLLECT EXCEL COLUMN
               ------------------------------------------------ */

            const excelColumn =
                document
                    .getElementById('excelColumn')
                    .value
                    .trim();


            /* ------------------------------------------------
               COLLECT FIELD TYPE
               ------------------------------------------------ */

            const fieldType =
                document
                    .getElementById('fieldType')
                    .value;


            /* ------------------------------------------------
               COLLECT REQUIRED STATUS
               ------------------------------------------------ */

            const required =
                document
                    .getElementById('fieldRequired')
                    .checked;


            /* ------------------------------------------------
               COLLECT GRADING STATUS
               ------------------------------------------------ */

            const includeInGrading =
                document
                    .getElementById('fieldGrading')
                    .checked;


            /* ------------------------------------------------
               COLLECT DISPLAY ORDER
               ------------------------------------------------ */

            const displayOrder =
                Number(
                    document
                        .getElementById('displayOrder')
                        .value
                );


            /* ------------------------------------------------
               BASIC FRONTEND VALIDATION
               ------------------------------------------------ */

            if (!fieldName) {

                alert('Please enter a field name.');

                return;
            }


            if (!excelColumn) {

                alert('Please enter the Excel column.');

                return;
            }


            /* ------------------------------------------------
               CHECK IF EDITING OR CREATING
               ------------------------------------------------ */

            const editingId =
                document.getElementById(
                    'fieldId'
                ).value;

            const isEditing =
                editingId !== '';

            /*
                Build the URL and method:

                - POST  /api/report-fields          (create)
                - PUT   /api/report-fields/<id>      (update)
            */

            const url = isEditing
                ? '/api/report-fields/' + editingId
                : '/api/report-fields';

            const method = isEditing
                ? 'PUT'
                : 'POST';

            const payload = isEditing
                ? {
                    field_name:
                        fieldName,
                    excel_column:
                        excelColumn,
                    field_type:
                        fieldType,
                    required:
                        required,
                    include_in_grading:
                        includeInGrading,
                    display_order:
                        displayOrder
                }
                : {
                    template_id:
                        Number(templateId),
                    field_name:
                        fieldName,
                    excel_column:
                        excelColumn,
                    field_type:
                        fieldType,
                    required:
                        required,
                    include_in_grading:
                        includeInGrading,
                    display_order:
                        displayOrder
                };

            /* ------------------------------------------------
               SEND DATA TO FLASK
               ------------------------------------------------ */

            try {

                const response =
                    await fetch(
                        url,
                        {
                            method: method,

                            headers: {
                                'Content-Type':
                                    'application/json'
                            },

                            body:
                                JSON.stringify(
                                    payload
                                )
                        }
                    );


                /* --------------------------------------------
                   READ FLASK RESPONSE
                   -------------------------------------------- */

                const result =
                    await response.json();


                /* --------------------------------------------
                   HANDLE ERROR
                   -------------------------------------------- */

                if (!response.ok) {

                    alert(
                        result.error ||
                        'Unable to save field.'
                    );

                    return;
                }


                /* --------------------------------------------
                   SUCCESS
                   -------------------------------------------- */

                alert(
                    isEditing
                        ? 'Field updated successfully!'
                        : 'Field created successfully!'
                );


                /*
                    Reload the page.

                    Flask will retrieve the fields from
                    SQLite and display the new field.
                */

                window.location.reload();

            }

            catch (error) {

                console.error(
                    'Error saving field:',
                    error
                );

                alert(
                    'Something went wrong while creating the field.'
                );
            }

        }
    );


/* =========================================================
   EDIT FIELD
   ========================================================= */

async function editField(fieldId) {

    try {

        const response =
            await fetch(
                '/api/report-fields/' + fieldId
            );

        const result =
            await response.json();

        if (!response.ok) {

            alert(
                result.error ||
                'Unable to load field.'
            );

            return;
        }

        const field = result.field;

        /*
            Populate the modal with the field's
            current values.
        */

        document.getElementById(
            'fieldId'
        ).value = field.id;

        document.getElementById(
            'fieldName'
        ).value = field.field_name;

        document.getElementById(
            'excelColumn'
        ).value = field.excel_column;

        document.getElementById(
            'fieldType'
        ).value = field.field_type;

        document.getElementById(
            'fieldRequired'
        ).checked = Boolean(field.required);

        document.getElementById(
            'fieldGrading'
        ).checked = Boolean(
            field.include_in_grading
        );

        document.getElementById(
            'displayOrder'
        ).value = field.display_order;

        /*
            Change the modal heading to indicate
            we are editing.
        */

        const modalTitle =
            document.getElementById('modalTitle');

        if (modalTitle) {
            modalTitle.textContent =
                'Edit Report Field';
        }

        /*
            Open the modal.
        */

        const modal =
            document.getElementById('fieldModal');

        modal.classList.add('active');

    }
    catch (error) {

        console.error(
            'Error loading field:', error
        );

        alert(
            'Something went wrong while loading the field.'
        );
    }
}


/* =========================================================
   DELETE FIELD
   ========================================================= */

async function deleteField(fieldId) {

    /*
        Ask the user for confirmation before deleting.
    */

    const confirmed =
        confirm(
            'Are you sure you want to delete this field?'
        );


    if (!confirmed) {

        return;
    }


    try {

        const response =
            await fetch(
                '/api/report-fields/' + fieldId,
                {
                    method: 'DELETE'
                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            alert(
                result.error ||
                'Unable to delete field.'
            );

            return;
        }


        alert(
            'Field deleted successfully.'
        );


        /*
            Refresh the page so that the deleted
            field disappears.
        */

        window.location.reload();

    }

    catch (error) {

        console.error(
            'Error deleting field:',
            error
        );

        alert(
            'Something went wrong while deleting the field.'
        );
    }
}


/* =========================================================
   CONTINUE TO GRADING
   ========================================================= */

function continueToGrading() {

    /*
        The next stage of SnapReport will be the
        grading configuration screen.

        Example:

            /configure/8/grading
    */

    window.location.href =
        '/configure/' +
        templateId +
        '/grading';
}