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
               SEND DATA TO FLASK
               ------------------------------------------------ */

            try {

                const response =
                    await fetch(
                        '/api/report-fields',
                        {
                            method: 'POST',

                            headers: {
                                'Content-Type':
                                    'application/json'
                            },

                            body: JSON.stringify({

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
                            })
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
                        'Unable to create field.'
                    );

                    return;
                }


                /* --------------------------------------------
                   SUCCESS
                   -------------------------------------------- */

                alert(
                    'Field created successfully!'
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
                    'Error creating field:',
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

function editField(fieldId) {

    /*
        This is intentionally not implemented yet.

        Later we will:

        1. Get the field from SQLite.
        2. Populate the modal.
        3. Change "Add Field" to "Edit Field".
        4. Send PUT/PATCH request.
        5. Update SQLite.
    */

    alert(
        'Edit field ' + fieldId +
        ' will be implemented next.'
    );
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