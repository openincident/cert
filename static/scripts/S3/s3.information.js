$('.contact').each(function () {
    var contact = $(this);
    var id = contact.attr('id').match(/\d+/);
    contact.find('a.editBtn').click(function (e) {
        var span = contact.find('span');
        var current = span.html();

        var formHolder = $('<div>').addClass('form-container');

        var form = $('<form>');
        formHolder.append(form);

        var input = $('<input>');
        input.val(current);
        form.append(input);

        var save = $('<input type="submit">');
        save.val('Save');
        form.append(save);

        span.replaceWith(formHolder);
        contact.addClass('edit');

        form.submit(function (e) {
            e.preventDefault();
            contact.removeClass('edit').addClass('saving');
            form.append($('<img src="' + S3.Ap.concat('/static/img/jquery-ui/ui-anim_basic_16x16.gif') + '">').addClass('fright'));
            form.find('input[type=submit]').addClass('hidden');
            $.post(S3.Ap.concat('/hrm/contact/' + id[0] + '.s3json'),
                   '{"$_pr_contact":' + JSON.stringify({'value': input.val()}) + '}',
                   function () {
                      contact.removeClass('saving');
                      // FIXME: Use returned value!
                      var value = input.val();
                      formHolder.replaceWith($('<span>').html(value));
                   }, 'json');
        });
    });
});

$('.addresses').each(function () {
    var address = $(this);
    address.find('a.edit').click(function () {
        // Show the edit form
        s3_gis_edit_tab();
        address.find('form').submit(function (e) {
            e.preventDefault();
            $.post(S3.Ap.concat('/hrm/person/' + personId + '/address/'),
                $(this).serialize()
            );
        });
    });
});

