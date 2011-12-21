<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
    xmlns:hrm="http://eden.sahanafoundation.org/org">

    <!-- **********************************************************************
         Event Participant List - CSV Import Stylesheet

         2011-12-03 / Dominic König <dominic AT aidiq DOT com>

         Column headers defined in this stylesheet:

         Column headers looked up in labels.xml:

         PersonGender...................optional.....person gender

    *********************************************************************** -->
    <xsl:output method="xml"/>
    <xsl:include href="./person.xsl"/>

    <!-- ****************************************************************** -->
    <!-- Event types, see models/06_hrm.py -->
    <hrm:event-type code="1">Training</hrm:event-type>
    <hrm:event-type code="2">Emergency Deployment</hrm:event-type>
    <hrm:event-type code="3">Planned Deployment</hrm:event-type>
    <hrm:event-type code="4">Outreach</hrm:event-type>
    <hrm:event-type code="5">SocialCERT</hrm:event-type>

    <!-- ****************************************************************** -->
    <!-- Index for faster processing -->
    <xsl:key name="events"
             match="row"
             use="concat(col[@field='Organisation'], '/',
                         col[@field='Event'], '/',
                         col[@field='DateTime'])"/>

    <!-- ****************************************************************** -->
    <xsl:template match="/">

        <s3xml>
            <!-- Organisations -->
            <xsl:for-each select="//row[generate-id(.)=
                                        generate-id(key('orgs',
                                                        col[@field='Organisation'])[1])]">
                <xsl:call-template name="Organisation"/>
            </xsl:for-each>

            <!-- Events -->
            <xsl:for-each select="//row[generate-id(.)=
                                        generate-id(key('events',
                                                        concat(col[@field='Organisation'], '/',
                                                               col[@field='Event'], '/',
                                                               col[@field='DateTime']))[1])]">
                <xsl:call-template name="Event"/>
            </xsl:for-each>

            <!-- Process all table rows for person records -->
            <xsl:apply-templates select="table/row"/>
        </s3xml>

    </xsl:template>

    <!-- ****************************************************************** -->
    <xsl:template name="Event">

        <xsl:variable name="OrgName" select="col[@field='Organisation']/text()"/>
        <xsl:variable name="EventName" select="col[@field='Event']/text()"/>
        <xsl:variable name="EventType" select="col[@field='EventType']/text()"/>
        <xsl:variable name="DateTime" select="col[@field='DateTime']/text()"/>

        <resource name="hrm_event">
            <xsl:attribute name="tuid">
                <xsl:value-of select="concat($OrgName, '/',
                                             $EventName, '/',
                                             $DateTime)"/>
            </xsl:attribute>
            <xsl:variable name="typecode" select="document('')//hrm:event-type[text()=normalize-space($EventType)]/@code"/>
            <xsl:if test="$typecode">
                <data field="type"><xsl:value-of select="$typecode"/></data>
            </xsl:if>
            <data field="datetime"><xsl:value-of select="$DateTime"/></data>
            <data field="name"><xsl:value-of select="$EventName"/></data>

            <reference field="organisation_id" resource="org_organisation">
                <xsl:attribute name="tuid">
                    <xsl:value-of select="$OrgName"/>
                </xsl:attribute>
            </reference>

        </resource>

    </xsl:template>

    <!-- ****************************************************************** -->
    <!-- Person Record -->
    <xsl:template match="row">

        <xsl:variable name="OrgName" select="col[@field='Organisation']/text()"/>
        <xsl:variable name="EventName" select="col[@field='Event']/text()"/>
        <xsl:variable name="DateTime" select="col[@field='DateTime']/text()"/>

        <xsl:variable name="gender">
            <xsl:call-template name="GetColumnValue">
                <xsl:with-param name="colhdrs" select="$PersonGender"/>
            </xsl:call-template>
        </xsl:variable>

        <resource name="hrm_experience">
            <reference field="event_id" resource="hrm_event">
                <xsl:attribute name="tuid">
                    <xsl:value-of select="concat($OrgName, '/',
                                                $EventName, '/',
                                                $DateTime)"/>
                </xsl:attribute>
            </reference>
            <reference field="person_id" resource="pr_person">
                <resource name="pr_person">
                    <data field="first_name"><xsl:value-of select="col[@field='First Name']"/></data>
                    <data field="last_name"><xsl:value-of select="col[@field='Last Name']"/></data>
                    <xsl:if test="$gender!=''">
                        <data field="gender">
                            <xsl:attribute name="value"><xsl:value-of select="$gender"/></xsl:attribute>
                        </data>
                    </xsl:if>
                    <xsl:call-template name="ContactInformation"/>
                </resource>
            </reference>
        </resource>

    </xsl:template>

    <!-- ****************************************************************** -->

</xsl:stylesheet>
