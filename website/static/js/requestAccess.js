'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var bootbox = require('bootbox');
var ko = require('knockout');
var Raven = require('raven-js');
var ChangeMessageMixin = require('js/changeMessage');

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

var RequestAccessViewModel = function(currentUserRequestState, nodeId, user) {
    var self = this;

    self.user = user;
    self.requestAccessButton = ko.observable('Request access');
    self.accessRequestPendingOrDenied = ko.observable(false);
    self.accessRequestTooltip = ko.observable('');
    self.updateUrl = $osf.apiV2Url('nodes/' +  nodeId + '/requests/');
    self.requestState = ko.observable(currentUserRequestState);

    self.checkRequestStatus = function() {

        if (self.requestState() === 'pending' || self.requestState() === 'rejected') {
            self.accessRequestPendingOrDenied(true);
            self.requestAccessButton = ko.observable('Access requested');
        }
        if (self.requestState() === 'rejected') {
            self.accessRequestTooltip('Request declined');
        }
    };

    self.requestProjectAccess = function() {
        if (self.requestState() === 'rejected') {
            return false;
        }
        self.accessRequestPendingOrDenied(true);
        $osf.trackClick('button', 'click', 'request-project-access');

        var payload = {
            data: {
                type: 'node-requests',
                attributes: {
                    request_type: 'access'
                }
            }
        };
        var request = $osf.ajaxJSON(
            'POST',
            self.updateUrl,
            {
                'isCors': true,
                'data': payload,
                'fields': {
                    xhrFields: {withCredentials: true}
                }
            }
        );

        request.done(function() {
            self.requestAccessButton('Access requested');
        }.bind(this));
        request.fail(function(xhr, status, error) {
            self.accessRequestPendingOrDenied(false);
            $osf.growl('Error',
                sprintf(_('Access request failed. Please contact %1$s if the problem persists.') , $osf.osfSupportLink() ),
                'danger'
            );
            Raven.captureMessage(_('Error requesting project access'), {
                extra: {
                    url: self.updateUrl,
                    status: status,
                    error: error
                }
            });
        }.bind(this));
        return request;
    };

    self.init = function() {
        self.checkRequestStatus();
        self.supportMessage = sprintf(_('If this should not have occurred, please contact %1$s.') , $osf.osfSupportLink() );
    };

    self.init();

};

module.exports = RequestAccessViewModel;

