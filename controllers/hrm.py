# -*- coding: utf-8 -*-

"""
    Human Resource Management

    @author: Dominic König <dominic AT aidiq DOT com>
    @author: Fran Boon <fran AT aidiq DOT com>
"""

module = request.controller
resourcename = request.function

if module not in deployment_settings.modules:
    raise HTTP(404, body="Module disabled: %s" % module)

roles = session.s3.roles or []
if session.s3.hrm is None:
    session.s3.hrm = Storage()
session.s3.hrm.mode = request.vars.get("mode", None)

# =============================================================================
def org_filter():
    """
        Find the Organisation(s) this user is entitled to view
        i.e. they have the organisation access role or a site access role
    """

    table = db.org_organisation
    orgs = db(table.owned_by_organisation.belongs(roles)).select(table.id)
    orgs = [org.id for org in orgs]

    stable = db.org_site
    siteorgs = db(stable.owned_by_facility.belongs(roles)).select(stable.organisation_id)
    for org in siteorgs:
        if org.organisation_id not in orgs:
            orgs.append(org.organisation_id)

    if orgs:
        session.s3.hrm.orgs = orgs
    else:
        session.s3.hrm.orgs = None

# =============================================================================
@auth.requires_login()
def s3_menu_prep():
    """ Application Menu """

    # Module Name
    try:
        module_name = deployment_settings.modules[module].name_nice
    except:
        module_name = T("Human Resources Management")
    response.title = module_name

    # Automatically choose an organisation
    if session.s3.hrm.orgs is None:
        org_filter()

    # Set mode
    if session.s3.hrm.mode != "personal" and \
       (ADMIN in roles or session.s3.hrm.orgs):
        session.s3.hrm.mode = None
    else:
        session.s3.hrm.mode = "personal"

s3_menu(module, prep=s3_menu_prep)

# =============================================================================
def index():
    """ Dashboard """

    if session.error:
        return dict()

    mode = session.s3.hrm.mode
    if mode is not None:
        redirect(URL(f="person"))

    # Load Models
    s3mgr.load("hrm_skill")

    tablename = "hrm_human_resource"
    table = db.hrm_human_resource

    if ADMIN not in roles:
        orgs = session.s3.hrm.orgs or [None]
        org_filter = (table.organisation_id.belongs(orgs))
    else:
        # Admin can see all Orgs
        org_filter = (table.organisation_id > 0)

    s3mgr.configure(tablename,
                    insertable=False,
                    list_fields=["id",
                                 "person_id",
                                 "job_title",
                                 "type",
                                 "status"])

    response.s3.filter = org_filter
    # Parse the Request
    r = s3base.S3Request(s3mgr, prefix="hrm", name="human_resource")
    # Pre-process
    # Only set the method to search if it is not an ajax dataTable call
    # This fixes a problem with the dataTable where the the filter had a
    # distinct in the sql which cause a ticket to be raised
    if r.representation != "aadata":
        r.method = "search"
    r.custom_action = human_resource_search
    # Execute the request
    output = r()
    if r.representation == "aadata":
        return output
    # Post-process
    response.s3.actions = [dict(label=str(T("Details")),
                                _class="action-btn",
                                url=URL(f="person",
                                        args=["human_resource"],
                                        vars={"human_resource.id": "[id]"}))]

    if r.interactive:
        output.update(module_name=response.title)
        if session.s3.hrm.orgname:
            output.update(orgname=session.s3.hrm.orgname)
        response.view = "hrm/index.html"
        query = (table.deleted != True) & \
                (table.status == 1) & org_filter
        ns = db(query & (table.type == 1)).count()
        nv = db(query & (table.type == 2)).count()
        output.update(ns=ns, nv=nv)

        module_name = deployment_settings.modules[module].name_nice
        output.update(title=module_name)

    return output

# =============================================================================
# Events
# =============================================================================
def event():
    """ RESTful Controller """

    s3mgr.load("hrm_event")

    s3mgr.model.set_method(module, resourcename,
                           method="deployment",
                           action=deployment)

    def prep(r):
        if r.interactive:
            if not r.component:
                script = "s3.certreq.js"
                response.s3.scripts.append( "%s/%s" % (response.s3.script_dir, script))
                if r.record is not None:
                    certificate_id = r.record.certificate_id
                    if certificate_id:
                        rtable = db.hrm_certificate_requirement
                        query = (rtable.deleted != True) & \
                                (rtable.certificate_id == certificate_id)
                        r.table.requirement_id.requires = IS_NULL_OR(IS_ONE_OF(db(query),
                                                                "hrm_certificate_requirement.id",
                                                                "%(event_type)s",
                                                                orderby="hrm_certificate_requirement.event_type"))
            if r.component:
                if r.component_name == "shift":
                    if not r.record.shift_locations:
                        field = db.hrm_shift.location_id
                        field.readable = False
                        field.writable = False
                        field.default = r.record.location_id
                elif r.component_name == "certificate":
                    s3.crud_strings["hrm_certificate"].update(
                        title_create = T("Add Certificate to Event"),
                        title_display = T("Certificate Details"),
                        title_list = T("Certificates"),
                        title_update = T("Edit Certificate"),
                        subtitle_create = T("Add New Certificate"),
                        subtitle_list = T("Event Certificates"),
                        label_list_button = T("All Certificates"),
                        label_create_button = T("Add Certificate"),
                        label_delete_button = T("Remove Certificate"),
                        msg_record_created = T("Certificate Added To Event"),
                        msg_record_modified = T("Certificate Updated"),
                        msg_record_deleted = T("Certificate Removed"),
                        msg_no_match = T("No entries found"),
                        msg_list_empty = T("Currently No Certificates registered"))
                elif r.component_name == "participant":
                    s3mgr.load("hrm_experience")
                    etable = db.hrm_experience
                    etable.person_id.comment = None
                    etable.person_id.widget = S3AddPersonWidget()
                    etable.person_id.requires = IS_ADD_PERSON_WIDGET()

                    s3.crud_strings["hrm_experience"] = Storage(
                        title_create = T("Add Participant"),
                        title_display = T("Participant Details"),
                        title_list = T("Participants"),
                        title_update = T("Edit Participant"),
                        title_search = T("Search Participants"),
                        subtitle_create = T("Add Participant"),
                        subtitle_list = T("Participants"),
                        label_list_button = T("List Participants"),
                        label_create_button = T("Add Participant"),
                        label_delete_button = T("Delete Participant"),
                        msg_record_created = T("Participant added"),
                        msg_record_modified = T("Participant updated"),
                        msg_record_deleted = T("Participant deleted"),
                        msg_no_match = T("No entries found"),
                        msg_list_empty = T("Currently no Participants registered for this event"))

        if r.http == "POST":
            type = request.post_vars.get("type", None)
            shifts = request.post_vars.get("shifts", None)
            if type == "1":
                # Training events should direct to the Equivalence table
                s3mgr.configure("hrm_event",
                                create_next = URL(args=["[id]", "certificate"]))
            elif shifts:
                # Open the Shifts tab
                s3mgr.configure("hrm_event",
                                create_next = URL(args=["[id]", "shift"]))
            else:
                # Open the Deployment tab
                s3mgr.configure("hrm_event",
                                create_next = URL(args=["[id]", "deployment"]))
                s3mgr.configure("hrm_course_certificate",
                                create_next = URL(args=[r.id, "deployment"]))

        return True
    response.s3.prep = prep

    output = s3_rest_controller(module, resourcename,
                                rheader=event_rheader)
    return output

def event_over_check(event):
    """
        Determine whether the event is over & hence  can be added as
        participants to an Event
    """
    if not event.shifts:
        if not event.datetime:
            # We have no idea, so default to allowing
            return True
        if event.hours:
            if request.utcnow > event.datetime + datetime.timedelta(hours = event.hours):
                return True
        elif request.utcnow > event.datetime:
            return True
        return False
    else:
        # @ToDo
        return True

# -----------------------------------------------------------------------------
def event_rheader(r):
    """ Resource Header for Events """

    rheader = None
    if r.representation == "html":
        if r.name == "event":
            event = r.record
            if event:
                # Event Controller
                tabs = [(T("Event Details"), None)]
                if event.shifts:
                    tabs.append((T("Shifts"), "shift"))
                if event.type == 1: # Training
                    tabs.append((T("Qualifications"), "certificate"))
                tabs.append((T("Deployment"), "deployment"))
                if event_over_check(event):
                    # Allow people to be registered as having attended the event
                    tabs.append((T("Participants"), "participant"))
                rheader_tabs = s3_rheader_tabs(r, tabs)

                rheader = DIV(TABLE(TR(TH("%s: " % T("Name")),
                                       event.name,
                                       TH("%s: " % T("Type")),
                                       db.hrm_event.type.represent(event.type)),
                                    TR(TH("%s: " % T("Initiating Entity")),
                                       organisation_represent(event.organisation_id),),
                                    TR(TH("%s: " % T("Notes")),
                                       event.comments),
                                    ), rheader_tabs)

    return rheader

# -----------------------------------------------------------------------------
def deployment(r, **attr):
    """
        Custom method of Events to handle Deployments
        http://eden.sahanafoundation.org/wiki/BluePrintCERT/RHoK2011#a2.Deployment
    """

    if r.representation == "html" and \
       r.name == "event" and r.id and not r.component:

        s3mgr.load("msg_outbox")
        msg_compose = response.s3.msg_compose

        record = r.record
        if record.datetime:
            date = " at %s" % s3_datetime_represent(record.datetime)
        else:
            date = ""
        text = "%s%s: %s" % (record.name,
                             date,
                             record.comments)

        message = msg.prepare_opengeosms(record.location_id,
                                         code="ST",
                                         map="google",
                                         text=text)

        # Pass in the appropriate Contact List
        gtable = db.pr_group
        query = (gtable.uuid == record.type)
        recipient = db(query).select(gtable.pe_id,
                                     limitby=(0, 1)).first()
        if recipient:
            recipient = recipient.pe_id

        output = msg_compose(type="SMS",
                             recipient = recipient,
                             recipient_type = "pr_group",
                             message = message,
                             redirect_module = "hrm",
                             redirect_function = "event",
                             redirect_args = r.id)

        # Maintain RHeader for consistency
        rheader = event_rheader(r)

        title = T("Send Deployment Notification")

        output.update(title=title,
                      rheader=rheader)

        #if form.accepts(request.vars, session):

        response.view = "msg/compose.html"
        return output

    else:
        raise HTTP(501, BADMETHOD)

# -----------------------------------------------------------------------------
def experience():
    """
        Upload of a class participant list

        @todo: add certificate selector to both, manual import & upload
        @todo: implement list_fields
        @todo: implement event-based/date-based filters (S3Search)
    """

    s3mgr.load("hrm_experience")

    s3.crud_strings["hrm_experience"].update(
        title_report=T("Volunteer Report"),
        subtitle_report=T("Volunteer Hours"),
        title_upload = T("Upload Participant List"))

    s3mgr.configure("hrm_experience",
                    insertable=False, editable=False, deletable=False)

    output = s3_rest_controller(module, resourcename,
                                csv_template = "experience",
                                csv_extra_fields = [
                                        dict(label="Event",
                                             field=db.hrm_experience.event_id)
                                    ])
    return output

# =============================================================================
# People
# =============================================================================
def human_resource():
    """ HR Controller """

    # Load Models
    s3mgr.load("pr_address")
    s3mgr.load("hrm_skill")

    tablename = "hrm_human_resource"
    table = db[tablename]
    ptable = db.pr_person

    # Configure CRUD strings
    s3.crud_strings[tablename] = Storage(
        title_create = T("Add Staff Member"),
        title_display = T("Staff Member Details"),
        title_list = T("Staff & Volunteers"),
        title_update = T("Edit Record"),
        title_search = T("Search Staff & Volunteers"),
        subtitle_create = T("Add New Staff Member"),
        subtitle_list = T("Staff Members"),
        label_list_button = T("List All Records"),
        label_create_button = T("Add Staff Member"),
        label_delete_button = T("Delete Record"),
        msg_record_created = T("Staff member added"),
        msg_record_modified = T("Record updated"),
        msg_record_deleted = T("Record deleted"),
        msg_list_empty = T("No staff or volunteers currently registered"))

    # NB Change these & change the list_fields.pop() later
    list_fields = ["id",
                   "person_id",
                   "job_title",
                   "organisation_id",
                   "site_id",
                   "location_id",
                   "type",
                   "status",
                  ]

    # Must specify a group to create HRs
    # Interactive
    group = request.vars.get("group", None)
    if group == None:
        # Imports
        groupCode = request.vars.get("human_resource.type", None)
        if groupCode == "2":
            group = "volunteer"
        elif groupCode == "1":
            group = "staff"
    if group == "volunteer":
        table.type.default = 2
        response.s3.filter = (table.type == 2)
        table.location_id.writable = True
        table.location_id.readable = True
        table.location_id.label = T("Home Address")
        list_fields.pop(4)
        s3.crud_strings[tablename].update(
            title_create = T("Add Volunteer"),
            title_display = T("Volunteer Information"),
            title_list = T("Volunteers"),
            title_search = T("Search Volunteers"),
            subtitle_create = T("Add New Volunteer"),
            subtitle_list = T("Volunteers"),
            label_create_button = T("Add Volunteer"),
            msg_record_created = T("Volunteer added"))
        # Remove Type filter from the Search widget
        human_resource_search = s3mgr.model.get_config(tablename,
                                                       "search_method")
        human_resource_search._S3Search__advanced.pop(1)
        s3mgr.configure(tablename,
                        search_method = human_resource_search)
        # Fix the breadcrumb
        #breadcrumbs[2] = (T("Volunteers"), False,
        #                  URL(c=request.controller,
        #                      f=request.function,
        #                      args=request.args,
        #                      vars=request.vars))
        #if "create" in request.args:
        #    breadcrumbs[3] = (T("New Volunteer"), True,
        #                      URL(c=request.controller,
        #                          f=request.function,
        #                          args=request.args,
        #                          vars=request.vars))

    elif group == "staff":
        #s3mgr.configure(table._tablename, insertable=False)
        # Default to Staff
        table.type.default = 1
        response.s3.filter = (table.type == 1)
        table.site_id.writable = True
        table.site_id.readable = True
        list_fields.pop(5)
        list_fields.append("end_date")
        s3.crud_strings[tablename].update(
            title_create = T("Add Staff Member"),
            title_list = T("Staff"),
            title_search = T("Search Staff"),
            title_upload = T("Import Staff & Volunteers"),
        )
        if "expiring" in request.get_vars:
            response.s3.filter = response.s3.filter & \
                                 (table.end_date < (request.utcnow + datetime.timedelta(weeks=4)))
            s3.crud_strings[tablename].title_list = T("Staff with Contracts Expiring in the next Month")
            # Remove the big Add button
            s3mgr.configure(tablename,
                            insertable=False)
        # Remove Type filter from the Search widget
        human_resource_search = s3mgr.model.get_config(tablename,
                                                       "search_method")
        human_resource_search._S3Search__advanced.pop(1)
        s3mgr.configure(tablename,
                        search_method = human_resource_search)
        # Fix the breadcrumb
        #breadcrumbs[2] = (T("Staff"), False,
        #                  URL(c=request.controller,
        #                      f=request.function,
        #                      args=request.args,
        #                      vars=request.vars))

    s3mgr.configure(tablename,
                    list_fields = list_fields)

    def prep(r):
        if r.interactive:
            # Assume volunteers only between 12-81
            db.pr_person.date_of_birth.widget = S3DateWidget(past=972, future=-144)

            r.table.site_id.comment = DIV(DIV(_class="tooltip",
                                              _title="%s|%s|%s" % (T("Facility"),
                                                                   T("The site where this position is based."),
                                                                   T("Enter some characters to bring up a list of possible matches."))))
            if r.method != "read":
                # Don't want to see in Create forms
                # inc list_create (list_fields over-rides)
                r.table.status.writable = False
                r.table.status.readable = False

            if r.method == "create" and r.component is None:
                if group in (1, 2):
                    table.type.readable = False
                    table.type.writable = False
            elif r.representation == "plain":
                # Don't redirect Map popups
                pass
            elif r.id:
                vars = {"human_resource.id": r.id}
                if group:
                    vars.update(group=group)
                redirect(URL(f="person",
                             #args=["human_resource"],
                             vars=vars))
        return True
    response.s3.prep = prep

    def postp(r, output):
        if r.interactive:
            if not r.component:
                s3_action_buttons(r, deletable=False)
                if "msg" in deployment_settings.modules:
                    # @ToDo: Remove this now that we have it in Events?
                    response.s3.actions.append({
                        "url": URL(f="compose",
                                   vars = {"hrm_id": "[id]"}),
                        "_class": "action-btn",
                        "label": str(T("Send Notification"))})
        elif r.representation == "plain":
            # Map Popups
            output = hrm_map_popup(r)
        return output
    response.s3.postp = postp

    output = s3_rest_controller(module, resourcename)
    return output

# -----------------------------------------------------------------------------
def hrm_map_popup(r):
    """
        Custom output to place inside a Map Popup
        - called from postp of human_resource controller
    """

    # Load Model
    s3mgr.load("pr_address")
    #s3mgr.load("hrm_skill")

    output = TABLE()
    # Edit button
    output.append(TR(TD(A(T("Edit"),
                        _target="_blank",
                        _id="edit-btn",
                        _href=URL(args=[r.id, "update"])))))

    # First name, last name
    output.append(TR(TD(B("%s:" % T("Name"))),
                     TD(s3_fullname(r.record.person_id))))

    # Occupation (Job Title?)
    if r.record.job_title:
        output.append(TR(TD(B("%s:" % r.table.job_title.label)),
                         TD(r.record.job_title)))

    # Organization (better with just name rather than Represent)
    table = db.org_organisation
    query = (table.id == r.record.organisation_id)
    name = db(query).select(table.name,
                            limitby=(0, 1)).first().name
    output.append(TR(TD(B("%s:" % r.table.organisation_id.label)),
                     TD(name)))

    if r.record.location_id:
        table = db.gis_location
        query = (table.id == r.record.location_id)
        location = db(query).select(table.path,
                                    table.addr_street,
                                    limitby=(0, 1)).first()
        # City
        # Street address
        if location.addr_street:
            output.append(TR(TD(B("%s:" % table.addr_street.label)),
                             TD(location.addr_street)))
    # Mobile phone number
    table = db.pr_person
    query = (table.id == r.record.person_id)
    pe_id = db(query).select(table.pe_id,
                             limitby=(0, 1)).first().pe_id
    table = db.pr_contact
    query = (table.pe_id == pe_id)
    contacts = db(query).select(table.contact_method,
                                table.value)
    email = mobile_phone = ""
    for contact in contacts:
        if contact.contact_method == "EMAIL":
            email = contact.value
        elif contact.contact_method == "SMS":
            mobile_phone = contact.value
    if mobile_phone:
        output.append(TR(TD(B("%s:" % pr_contact_method_opts.get("SMS"))),
                         TD(mobile_phone)))
    # Office number
    if r.record.site_id:
        table = db.org_office
        query = (table.site_id == r.record.site_id)
        office = db(query).select(table.phone1,
                                  limitby=(0, 1)).first()
        if office and office.phone1:
            output.append(TR(TD(B("%s:" % T("Office Phone"))),
                             TD(office.phone1)))
        else:
            # @ToDo: Support other Facility Types (Hospitals & Shelters)
            pass
    # Email address (as hyperlink)
    if email:
        output.append(TR(TD(B("%s:" % pr_contact_method_opts.get("EMAIL"))),
                         TD(A(email, _href="mailto:%s" % email))))

    return output

# -----------------------------------------------------------------------------
def information(r, **attr):
    """
        Custom Method to provide the deatils for the Person's 'Information' Tab:
            http://eden.sahanafoundation.org/wiki/BluePrintCERT/RHoK2011#Infotab
        This should provide a single view on:
            Address (pr_address)
            Contacts (pr_contact)
            Emergency Contacts
    """

    import itertools

    if r.http != "GET":
        r.error(405, s3mgr.ERROR.BAD_METHOD)

    person = r.record

    atable = db.pr_address
    ctable = db.pr_contact
    ltable = db.pr_group_membership

    # Do the contacts
    query = (ctable.pe_id == person.pe_id)
    contacts = db(query).select(orderby=ctable.contact_method)

    from itertools import groupby

    contact_groups = {}
    for key, group in groupby(contacts, lambda c: c.contact_method):
        contact_groups[key] = list(group)

    contacts_wrapper = DIV(_class="contacts")

    for contact_type, details in contact_groups.items():
        contacts_wrapper.append(H3(msg.CONTACT_OPTS[contact_type]))
        for detail in details:
            contacts_wrapper.append(P(
                SPAN(detail.value),
                A(T("Edit"), _class="editBtn"),
                _id="contact-%s" % detail.id,
                _class="contact",
                ))

    # Do the addresses
    query = (atable.pe_id == person.pe_id)
    addresses = db(query).select()

    address_wrapper = DIV(_class="addresses")

    # We don't want to edit/view comments on the address here.
    atable.comments.writable = False
    atable.comments.readable = False
    atable.id.readable = False
    s3mgr.configure(atable, update_next=URL(c="hrm", f="person",
                                            args=[person.id, "information"]))

    if addresses:
        address_wrapper.append(H3(T("Home Address")))

        for address in addresses:
            building_name = address.building_name or ""
            _address = address.address or ""
            address_wrapper.append(P("%s, %s" % (building_name,
                                                 _address)))
            address_wrapper.append(A(T("Edit"), _class="editBtn"))
            # Get the address form
            address_wrapper.append(DIV(
                SQLFORM(atable, address, _class="hidden"),
                _class="form-container",
                _id="address-edit"
            ))

    query = (ltable.person_id == r.id)
    lists = db(query).select()

    lists_wrapper = DIV(_class="lists")
    ltable.comments.writable = False
    ltable.comments.readable = False
    ltable.id.readable = False

    if lists:
        lists_wrapper.append(H3(T("Contact Groups")))
        list_string = ", ".join(map(lambda l: l.group_id.name, lists))
        lists_wrapper.append(P(list_string))

    # Custom View
    response.view = "hrm/information.html"

    # RHeader for consistency
    rheader = hrm_rheader(r)

    # Put whatever you want in here
    information = DIV(address_wrapper, contacts_wrapper, lists_wrapper,
                      _class="information-wrapper")

    # Add the javascript
    response.s3.scripts.append(URL(c="static", f="scripts",
                               args=["S3", "s3.information.js"]))
    response.s3.js_global.append("personId = %s;" % person.id);

    return dict(
            title = T("Volunteer Profile"),
            rheader = rheader,
            information = information,
        )

# -----------------------------------------------------------------------------
def events(r, **attr):
    """
        Custom Method to provide the details for the Person's 'Events' Tab:
            http://eden.sahanafoundation.org/wiki/BluePrintCERT/RHoK2011#Eventstab
        This should provide a formatted view of the person's upcoming events
    """

    person = r.record

    table = db.hrm_event

    # Put whatever you want in here
    events = DIV("tbc")

    # Custom View
    response.view = "hrm/events.html"

    # RHeader for consistency
    rheader = hrm_rheader(r)

    return dict(
            title = T("Volunteer Profile"),
            rheader = rheader,
            events = events
        )

# -----------------------------------------------------------------------------
def person():
    """
        Person Controller
        - used for Personal Profile & Imports
        - includes components relevant to HRM

        @ToDo: Volunteers should be redirected to vol/person?
    """

    s3mgr.model.add_component("hrm_human_resource",
                              pr_person="person_id")

    s3mgr.configure("pr_person",
                    # Stay on the record with tabs visible
                    update_next = URL(args=["[id]", "update"]))

    if deployment_settings.has_module("asset"):
        # Assets as component of people
        s3mgr.model.add_component("asset_asset",
                                  pr_person="assigned_to_id")
        # Edits should always happen via the Asset Log
        # @ToDo: Allow this method too, if we can do so safely
        s3mgr.configure("asset_asset",
                        insertable = False,
                        editable = False,
                        deletable = False)

    s3mgr.model.set_method("pr", resourcename,
                           method="information",
                           action=information)

    s3mgr.model.set_method("pr", resourcename,
                           method="events",
                           action=events)

    group = request.get_vars.get("group", "staff")
    hr_id = request.get_vars.get("human_resource.id", None)
    if not str(hr_id).isdigit():
        hr_id = None

    mode = session.s3.hrm.mode

    # Configure human resource table
    tablename = "hrm_human_resource"
    table = db[tablename]
    if hr_id and str(hr_id).isdigit():
        hr = table[hr_id]
        if hr:
            group = hr.type == 2 and "volunteer" or "staff"

    org = session.s3.hrm.org
    if org is not None:
        table.organisation_id.default = org
        table.organisation_id.comment = None
        table.organisation_id.readable = False
        table.organisation_id.writable = False
        table.site_id.requires = IS_EMPTY_OR(IS_ONE_OF(db,
                                    "org_site.%s" % super_key(db.org_site),
                                    org_site_represent,
                                    filterby="organisation_id",
                                    filter_opts=[session.s3.hrm.org]))
    table.type.readable = True
    table.type.writable = True
    if group == "staff" and hr_id:
        table.site_id.writable = True
        table.site_id.readable = True
    elif group == "volunteer" and hr_id:
        table.location_id.writable = True
        table.location_id.readable = True
    elif not hr_id:
        table.location_id.readable = True
        table.site_id.readable = True
    if session.s3.hrm.mode is not None:
        s3mgr.configure(tablename,
                        list_fields=["id",
                                     "organisation_id",
                                     "type",
                                     "job_title",
                                     "status",
                                     "location_id",
                                     "site_id"])
    else:
        s3mgr.configure(tablename,
                        list_fields=["id",
                                     "type",
                                     "job_title",
                                     "status",
                                     "location_id",
                                     "site_id"])

    # Configure person table
    # - hide fields
    tablename = "pr_person"
    table = db[tablename]
    table.pe_label.readable = False
    table.pe_label.writable = False
    table.missing.readable = False
    table.missing.writable = False
    table.age_group.readable = False
    table.age_group.writable = False
    s3mgr.configure(tablename,
                    deletable=False)

    if group == "staff":
        s3.crud_strings[tablename].update(
            title_upload = T("Import Staff"))
        # No point showing the 'Occupation' field - that's the Job Title in the Staff Record
        table.occupation.readable = False
        table.occupation.writable = False
        # Just have a Home Address
        s3mgr.load("pr_address")
        table = db.pr_address
        table.type.default = 1
        table.type.readable = False
        table.type.writable = False
        _crud = s3.crud_strings.pr_address
        _crud.title_create = T("Add Home Address")
        _crud.title_update = T("Edit Home Address")
        s3mgr.model.add_component("pr_address",
                                  pr_pentity=dict(joinby=super_key(db.pr_pentity),
                                                  multiple=False))
        address_tab_name = T("Home Address")
        # Default type for HR
        table = db.hrm_human_resource
        table.type.default = 1
        request.get_vars.update(xsltmode="staff")
    else:
        s3.crud_strings[tablename].update(
            title_upload = T("Import Volunteers"))
        address_tab_name = T("Addresses")
        # Default type for HR
        table = db.hrm_human_resource
        table.type.default = 2
        request.get_vars.update(xsltmode="volunteer")

    if session.s3.hrm.mode is not None:
        # Configure for personal mode
        # - unused by CERT currently
        db.hrm_human_resource.organisation_id.readable = True
        s3.crud_strings[tablename].update(
            title_display = T("Personal Profile"),
            title_update = T("Personal Profile"))
        # People can view their own HR data, but not edit it
        s3mgr.configure("hrm_human_resource",
                        insertable = False,
                        editable = False,
                        deletable = False)
        s3mgr.configure("hrm_certification",
                        insertable = True,
                        editable = True,
                        deletable = True)
        s3mgr.configure("hrm_credential",
                        insertable = False,
                        editable = False,
                        deletable = False)
        s3mgr.configure("hrm_competency",
                        insertable = True,  # Can add unconfirmed
                        editable = False,
                        deletable = False,
                        listadd = False)
        s3mgr.configure("hrm_training",    # Can add but not provide grade
                        insertable = True,
                        editable = False,
                        deletable = False)
        s3mgr.configure("hrm_experience",
                        insertable = False,
                        editable = False,
                        deletable = False)
        s3mgr.configure("pr_group_membership",
                        insertable = False,
                        editable = False,
                        deletable = False)

    else:
        # Configure for HR manager mode
        s3.crud_strings[tablename].update(
            title_upload = T("Import Staff & Volunteers"))
        if group == "staff":
            s3.crud_strings[tablename].update(
                title_display = T("Staff Member Details"),
                title_update = T("Staff Member Details"))
            hr_record = T("Staff Record")
        elif group == "volunteer":
            s3.crud_strings[tablename].update(
                title_display = T("Volunteer Details"),
                title_update = T("Volunteer Details"))
            hr_record = T("Volunteer Record")

        # These are all added via the Certifications
        s3mgr.configure("hrm_competency",
                        insertable = False,
                        editable = False,
                        deletable = False,
                        listadd = False)

        if deployment_settings.has_module("asset"):
            tabs.append((T("Assets"), "asset"))

    # Upload for configuration (add replace option)
    response.s3.importerPrep = lambda: dict(ReplaceOption=T("Remove existing data before import"))

    # Import pre-process
    def import_prep(data, group=group):
        """
            Deletes all HR records (of the given group) of the organisation
            before processing a new data import, used for the import_prep
            hook in s3mgr
        """

        request = current.request

        resource, tree = data
        xml = s3mgr.xml
        tag = xml.TAG
        att = xml.ATTRIBUTE

        if response.s3.import_replace:
            if tree is not None:
                if group == "staff":
                    group = 1
                elif group == "volunteer":
                    group = 2
                else:
                    return # don't delete if no group specified

                root = tree.getroot()
                expr = "/%s/%s[@%s='org_organisation']/%s[@%s='name']" % \
                       (tag.root, tag.resource, att.name, tag.data, att.field)
                orgs = root.xpath(expr)
                for org in orgs:
                    org_name = org.get("value", None) or org.text
                    if org_name:
                        try:
                            org_name = json.loads(s3mgr.xml.xml_decode(org_name))
                        except:
                            pass
                    if org_name:
                        query = (db.org_organisation.name == org_name) & \
                                (db.hrm_human_resource.organisation_id == db.org_organisation.id) & \
                                (db.hrm_human_resource.type == group)
                        resource = s3mgr.define_resource("hrm", "human_resource", filter=query)
                        ondelete = s3mgr.model.get_config("hrm_human_resource", "ondelete")
                        resource.delete(ondelete=ondelete, format="xml", cascade=True)

    s3mgr.import_prep = import_prep

    # CRUD pre-process
    def prep(r):
        if r.representation == "s3json":
            s3mgr.show_ids = True
        elif r.interactive:
            resource = r.resource

            # Assume volunteers only between 12-81
            r.table.date_of_birth.widget = S3DateWidget(past=972, future=-144)

            if mode is not None:
                r.resource.build_query(id=s3_logged_in_person())
            else:
                if not r.id and not hr_id:
                    # pre-action redirect => must retain prior errors
                    if response.error:
                        session.error = response.error
                    redirect(URL(r=r, f="human_resource"))
            if resource.count() == 1:
                resource.load()
                r.record = resource.records().first()
                if r.record:
                    r.id = r.record.id
            if not r.record:
                session.error = T("Record not found")
                redirect(URL(group, args=["search"]))
            elif r.component_name == "event":
                s3.crud_strings["hrm_experience"] = Storage(
                    title_create = T("Add Event"),
                    title_display = T("Event Details"),
                    title_list = T("Events"),
                    title_update = T("Edit Event"),
                    title_search = T("Search Events"),
                    subtitle_create = T("Add Event"),
                    subtitle_list = T("Events"),
                    label_list_button = T("List Events"),
                    label_create_button = T("Add Event"),
                    label_delete_button = T("Delete Event"),
                    msg_record_created = T("Event added"),
                    msg_record_modified = T("Event updated"),
                    msg_record_deleted = T("Event deleted"),
                    msg_no_match = T("No entries found"),
                    msg_list_empty = T("Currently no Events participated in"))
            if hr_id and r.component_name == "human_resource":
                r.component_id = hr_id
            s3mgr.configure("hrm_human_resource",
                            insertable = False)
            if not r.component_id or r.method in ("create", "update"):
                address_hide(db.pr_address)
        return True
    response.s3.prep = prep

    # REST Interface
    if session.s3.hrm.orgname and mode is None:
        orgname=session.s3.hrm.orgname
    else:
        orgname=None

    output = s3_rest_controller("pr", resourcename,
                                native=False,
                                rheader=hrm_rheader,
                                skills=hrm_skills,
                                orgname=orgname)
    return output

# -----------------------------------------------------------------------------
def contact():
    """ RESTful controller to allow S3JSON submission of contact records """
    response.s3.prep = lambda r: r.representation == "s3json"
    return s3_rest_controller("pr", "contact")

# -----------------------------------------------------------------------------
def hrm_rheader(r):
    """ Resource headers for component views """

    rheader = None

    if r.representation == "html":

        if r.name == "person":
            # Person Controller

            if session.s3.hrm.mode is not None:
                # Configure for personal use
                # (not used for CERT)
                tabs = [
                        #(T("Person Details"), None),
                        (T("Information"), "information"),
                        # Read-only view
                        (T("Skills"), "person/skill"),
                        #(T("Participation"), "experience"),
                        (T("Participation"), "event"),
                        (T("Events"), "events"),
                        ]
            else:
                # Configure for HR manager mode
                tabs = [
                        #(T("Person Details"), None),
                        #(hr_record, "human_resource"),
                        (T("Information"), "information"),
                        # Read-only view
                        (T("Skills"), "person/skill"),
                        # Edit view
                        # @ToDo: Custom Method for Qualifications?
                        #(T("Qualifications"), "qualification"),
                        #(T("Qualifications"), "competency"),
                        (T("Qualifications"), "certificate"),
                        #(T("Participation"), "experience"),
                        (T("Participation"), "event"),
                        (T("Notes"), "note"),
                        (T("Events"), "events"),
                        ]

            rheader_tabs = s3_rheader_tabs(r, tabs)

            person = r.record
            if person:
                # Calculate the Volunteer Hours
                # @ToDo: Consider doing this onaccept of Experience instead of calculated on Reads?
                table = db.hrm_human_resource
                row = db(table.person_id == person.id).select(table.status).first()
                s = ""
                if row:
                    status = db.hrm_human_resource.status.represent(row.status)
                table = db.hrm_experience
                eventIDs = db(table.person_id == person.id).select(table.event_id)
                hours = 0
                if eventIDs:
                    table = db.hrm_event
                    for eventID in eventIDs:
                        query = (table.id == eventID.event_id)
                        event = db(query).select(table.type,
                                                 table.datetime,
                                                 table.hours,
                                                 limitby=(0, 1)).first()
                        # Do not count social events as volunteer hours
                        if event.type != "SOCIAL":
                            if not event.datetime:
                                hours += int(event.hours)
                            elif event.datetime < datetime.datetime.now() and \
                                 event.datetime.year == datetime.datetime.now().year:
                                hours += int(event.hours)

                rheader = DIV(s3_avatar_represent(person.id,
                                                  "pr_person",
                                                  _class="fleft"),
                              TABLE(
                    TR(TH(s3_fullname(person))),
                    TR("%s: %s" % (T("Status"), status)),
                    TR("%s %s: %s" % (datetime.datetime.now().year,
                                      T("Volunteer Hours"),
                                      hours)),
                    ), rheader_tabs)

        elif r.name == "human_resource":
            # Human Resource Controller
            hr = r.record
            if hr:
                pass

        elif r.name == "organisation":
            # Organisation Controller
            org = r.record
            if org:
                pass

    return rheader

# -----------------------------------------------------------------------------
def hrm_skills(r):
    """
        Generate skills grid for hrm/person/skill tab.
    """

    if r.component_name == "skill" and not r.component_id:

        query = (db.hrm_competency.person_id == r.id)
        skillset = db(query).select(orderby=db.hrm_competency.skill_id.name)

        skills = []
        for skill in skillset:
            skills.append({
                "name": skill.skill_id.name,
                "level": skill.competency_id.name,
                "class": skill.competency_id.name.replace(" ", "").lower()
            })
        return skills
    return None

# =============================================================================
# Teams
# =============================================================================
def group():

    """
        Team controller
        - uses the group table from PR
    """

    tablename = "pr_group"
    table = db[tablename]

    table.group_type.label = T("Team Type")
    table.description.label = T("Team Description")
    table.name.label = T("Team Name")
    db.pr_group_membership.group_id.label = T("Team ID")
    db.pr_group_membership.group_head.readable == False
    db.pr_group_membership.group_head.writable == False
    #db.pr_group_membership.group_head.label = T("Team Leader")

    # Set Defaults
    table.group_type.default = 3  # 'Relief Team'
    table.group_type.readable = table.group_type.writable = False

    # CRUD Strings
    ADD_TEAM = T("Add Contact List")
    LIST_TEAMS = T("List Contact Lists")
    s3.crud_strings[tablename] = Storage(
        title_create = ADD_TEAM,
        title_display = T("Contact List Details"),
        title_list = LIST_TEAMS,
        title_update = T("Edit Contact List"),
        title_search = T("Search Contact Lists"),
        subtitle_create = T("Add New Contact List"),
        subtitle_list = T("Contact Lists"),
        label_list_button = LIST_TEAMS,
        label_create_button = ADD_TEAM,
        label_search_button = T("Search Contact Lists"),
        msg_record_created = T("Contact List added"),
        msg_record_modified = T("Contact List updated"),
        msg_record_deleted = T("Contact List deleted"),
        msg_list_empty = T("No Contact Lists currently registered"))

    s3.crud_strings["pr_group_membership"] = Storage(
        title_create = T("Add Member"),
        title_display = T("Membership Details"),
        title_list = T("Contact List Members"),
        title_update = T("Edit Membership"),
        title_search = T("Search Member"),
        subtitle_create = T("Add New Member"),
        subtitle_list = T("Current Contact List Members"),
        label_list_button = T("List Members"),
        label_create_button = T("Add Group Member"),
        label_delete_button = T("Delete Membership"),
        msg_record_created = T("Contact List Member added"),
        msg_record_modified = T("Membership updated"),
        msg_record_deleted = T("Membership deleted"),
        msg_list_empty = T("No Members currently registered"))

    response.s3.filter = (table.system == False) # do not show system groups

    s3mgr.configure(tablename, main="name", extra="description",
                    # Redirect to member list when a new group has been created
                    create_next = URL(f="group",
                                      args=["[id]", "group_membership"]))
    s3mgr.configure("pr_group_membership",
                    list_fields=["id",
                                 "person_id",
                                 "group_head",
                                 "description"])

    # Post-process
    def postp(r, output):

        if r.interactive:
            if not r.component:
                s3_action_buttons(r, deletable=False)
                if "msg" in deployment_settings.modules:
                    response.s3.actions.append({
                        "url": URL(f="compose",
                                   vars = {"group_id": "[id]"}),
                        "_class": "action-btn",
                        "label": str(T("Send Notification"))})

        return output
    response.s3.postp = postp

    tabs = [
            (T("Contact List Details"), None),
            # Team should be contacted either via the Leader or
            # simply by sending a message to the group as a whole.
            #(T("Contact Data"), "contact"),
            (T("Members"), "group_membership")]

    output = s3_rest_controller("pr", resourcename,
                                rheader=lambda r: pr_rheader(r, tabs = tabs))

    return output


# =============================================================================
# Jobs
# =============================================================================
def job_role():
    """ Job Roles Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    output = s3_rest_controller(module, resourcename)
    return output

# =============================================================================
# Skills
# =============================================================================
def skill():
    """ Skills Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    output = s3_rest_controller(module, resourcename)
    return output


def skill_type():
    """ Skill Types Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    output = s3_rest_controller(module, resourcename)
    return output

# -----------------------------------------------------------------------------
def competency_rating():
    """ Competency Rating for Skill Types Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    output = s3_rest_controller(module, resourcename)
    return output

# -----------------------------------------------------------------------------
def skill_competencies():
    """
        Called by S3FilterFieldChange to provide the competency options for a
            particular Skill Type
    """

    # Load Models
    s3mgr.load("hrm_skill")

    table = db.hrm_skill
    ttable = db.hrm_skill_type
    rtable = db.hrm_competency_rating
    query = (table.id == request.args[0]) & \
            (table.skill_type_id == ttable.id) & \
            (rtable.skill_type_id == table.skill_type_id)
    records = db(query).select(rtable.id,
                               rtable.name,
                               orderby=~rtable.priority)

    response.headers["Content-Type"] = "application/json"
    return records.json()

# -----------------------------------------------------------------------------
def skill_provision():
    """ Skill Provisions Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    output = s3_rest_controller(module, resourcename)
    return output

# -----------------------------------------------------------------------------
def course():
    """ Courses Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    output = s3_rest_controller(module, resourcename)
    return output

# -----------------------------------------------------------------------------
def course_certificate():
    """ Courses to Certificates Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    output = s3_rest_controller(module, resourcename)
    return output

# -----------------------------------------------------------------------------
def certificate():
    """ Certificates Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    output = s3_rest_controller(module, resourcename,
                                rheader=certificate_rheader)
    return output

def certificate_rheader(r):

    rheader = None

    if r.representation == "html" and r.name == "certificate":
        certificate = r.record
        tabs = [
                (T("Certificate"), None),
                (T("Requirements"), "certificate_requirement")
               ]
        if r.record is not None:
            rheader_tabs = s3_rheader_tabs(r, tabs)
            rheader = DIV(TABLE(
                        TR(
                            TH("%s: " % T("Certificate")),
                            TD(certificate.name)
                        )), rheader_tabs)
    return rheader

def requirements():
    """
        Returns a SELECT with the options of the selected
        certificate (=first URL argument). Called from JS
        to dynamically update the select list in the event form.
    """

    if len(request.args):
        from gluon.sqlhtml import OptionsWidget
        certificate_id = request.args[0]
        s3mgr.load("hrm_certificate_requirement")
        etable = db.hrm_event
        rtable = db.hrm_certificate_requirement
        query = (rtable.deleted != True) & \
                (rtable.certificate_id == certificate_id)
        if db(query).count():
            _has_options = 'true'
        else:
            _has_options = 'false'
        etable.requirement_id.requires = IS_NULL_OR(IS_ONE_OF(db(query),
                                            "hrm_certificate_requirement.id",
                                            "%(event_type)s",
                                            orderby="hrm_certificate_requirement.event_type")),
        widget = OptionsWidget.widget(etable.requirement_id, None,
                                      _has_options=_has_options)
        return widget

    return SELECT(OPTION(None, _value=""),
                  _id="hrm_event_requirement_id", _has_options='false')

# -----------------------------------------------------------------------------
def certificate_skill():
    """ Certificates to Skills Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    output = s3_rest_controller(module, resourcename)
    return output

# -----------------------------------------------------------------------------
def training():
    """ Training Controller """

    mode = session.s3.hrm.mode
    if mode is not None:
        session.error = T("Access denied")
        redirect(URL(f="index"))

    # Load Models
    s3mgr.load("hrm_skill")

    if ADMIN not in session.s3.roles and \
       EDITOR not in session.s3.roles:
        ttable = db.hrm_training
        hrtable = db.hrm_human_resource
        orgtable = db.org_organisation
        query = (ttable.person_id == hrtable.person_id) & \
                (hrtable.organisation_id == orgtable.id) & \
                (orgtable.owned_by_organisation.belongs(session.s3.roles))
        response.s3.filter = query

    output = s3_rest_controller(module, resourcename)
    return output

# =============================================================================
def staff_org_site_json():
    """
        Used by the Asset - Assign to Person page
    """

    table = db.hrm_human_resource
    otable = db.org_organisation
    #db.req_commit.date.represent = lambda dt: dt[:10]
    query = (table.person_id == request.args[0]) & \
            (table.organisation_id == otable.id)
    records = db(query).select(table.site_id,
                               otable.id,
                               otable.name)

    response.headers["Content-Type"] = "application/json"
    return records.json()

# =============================================================================
# Messaging
# =============================================================================
def compose():

    """ Send message to people/teams """

    s3mgr.load("msg_outbox")

    if "hrm_id" in request.vars:
        id = request.vars.hrm_id
        fieldname = "hrm_id"
        table = db.pr_person
        htable = db.hrm_human_resource
        query = (htable.id == id) & \
                (htable.person_id == table.id)
        title = T("Send a message to this person")
    elif "group_id" in request.vars:
        id = request.vars.group_id
        fieldname = "group_id"
        table = db.pr_group
        query = (table.id == id)
        title = T("Send a message to this contact list")

    pe = db(query).select(table.pe_id,
                          limitby=(0, 1)).first()
    if not pe:
        session.error = T("Record not found")
        redirect(URL(f="index"))

    pe_id = pe.pe_id
    request.vars.pe_id = pe_id

    if "hrm_id" in request.vars:
        # Get the individual's communications options & preference
        table = db.pr_contact
        contact = db(table.pe_id == pe_id).select(table.contact_method,
                                                  orderby="priority",
                                                  limitby=(0, 1)).first()
        if contact:
            db.msg_outbox.pr_message_method.default = contact.contact_method
        else:
            session.error = T("No contact method found")
            redirect(URL(f="index"))

    return response.s3.msg_compose(redirect_module = module,
                                   redirect_function = "compose",
                                   redirect_vars = {fieldname: id},
                                   title_name = title)

# END =========================================================================
