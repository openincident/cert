/**
 * Helper script for event form
 * Dynamically populates the requirement_id SELECT field
 * for the certificate selected
 */

$(function() {
    $('#hrm_event_requirement_id__row1').hide();
    $('#hrm_event_requirement_id__row').hide();
    function showReqSelect(certificate_id) {
        if (certificate_id != '') {
            var url = S3.Ap.concat('/hrm/requirements/' + certificate_id);
            $.getS3(url, function(data) {
                $(data).replaceAll('#hrm_event_requirement_id');
                if ($('#hrm_event_requirement_id').attr('has_options') == 'true') {
                    $('#hrm_event_requirement_id__row1').show();
                    $('#hrm_event_requirement_id__row').show();
                } else {
                    $('#hrm_event_requirement_id__row1').hide();
                    $('#hrm_event_requirement_id__row').hide();
                }
            }, 'html');
        }
    }
    $('#hrm_event_certificate_id').change(function() {
        certid = $('#hrm_event_certificate_id').val();
        if (certid != '') {
            showReqSelect(certid);
        }
    });
    certid = $('#hrm_event_certificate_id').val();
    if (certid != '') {
        $('#hrm_event_requirement_id__row1').show();
        $('#hrm_event_requirement_id__row').show();
    }
});
