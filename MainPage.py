#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import logging

from globals import get_team_list

from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import ndb
from google.appengine.api import users

from datastore_classes import league_key, Choice, root_event_key, Choice_key, account_key, Account

import jinja2
import webapp2

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

def get_taken_teams(league_id):
    """Returns a list of taken teams based on a league and event id"""
    taken_teams = []
    league_player_query = Account.query(Account.league == league_id)
    league_players = league_player_query.fetch()
    for player in league_players:
        choice = Choice_key(account_key(player.key.id()), league_id).get()
        if choice:
            taken_teams.append(str(choice.drafted_team))
    return taken_teams

def isValidTeam(team, league_id):
        """Parses and returns whether a team is present at a given event"""
        team_list = get_team_list('2014txsa')
        taken_list = get_taken_teams(league_id)
        try:
            number = int(team)
        except:
            return "Invalid number"
        if str(team) in taken_list:
            return "Team already taken (Possibly by you!)"
        if not (str(number) in team_list):
            return "Team not present at this event"
        return "Good" #Will indicate no errors

def group_list_in_n_size(list, size):
    """Groups a list into sub-lists of size: size"""
    grouped_list = []
    for i in range(size, len(list), size):
        team_segment = []
        for j in range(size, 0, -1):
            team_segment.append(list[i-j])
        grouped_list.append(team_segment)

    last_segment = []
    remaining_teams = len(list) % size
    for i in range(len(list)-remaining_teams, len(list)):
        last_segment.append(list[i])
    grouped_list.append(last_segment)
    return grouped_list

class MainPage(webapp2.RequestHandler):

    def get(self):
        # Checks for active Google account session
        user = users.get_current_user()

        #Force user login
        if user is None:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            #Current user's id, used to identify their data
            user_id = user.user_id()
            logout_url = users.create_logout_url('/')

            account = Account.get_or_insert(user_id)
            if account.nickname == None:
                account.nickname =  user.nickname()
                account.league = 0
                account.put()
            league_id = account.league

            #TODO Replace with choice of event
            event_id = '2014txsa'

            #Get user's choices for the current league
            find_Choice_key = Choice_key(account_key(user_id), str(league_id))
            found_Choice = find_Choice_key.get()

            #Display update text for the status of the last choice update
            update_text = self.request.get('updated')
            if self.request.get('updated') == "Good":
                update_text = "Update successful!"

            past_choice = ""
            if found_Choice:
                past_choice = found_Choice.drafted_team

            #Get list of teams at event
            team_numbers = get_team_list(event_id)

            #Get a list of those that are unavailable
            taken_teams = get_taken_teams(league_id)

            #Cross out those that are taken
            for i, number in enumerate(team_numbers):
                if (number in taken_teams):
                    team_numbers[i] = "<i><strike>" + number + "</strike></i>"

            #Separates teams into groups of five for easier listing
            team_list = group_list_in_n_size(team_numbers, 10)


            #Get list of players in the league and their choices
            league_table = [{'player_team': 'Drafted Team', 'player_name': 'Player'}]
            league_player_query = Account.query(Account.league == league_id)
            league_players = league_player_query.fetch() #league_player_query.order(Account.nickname).fetch()
            for player in league_players:
                choice = Choice_key(account_key(player.key.id()), league_id).get()
                if choice:
                    league_table.append({'player_team': str(choice.drafted_team), 'player_name': player.nickname})
                else:
                    league_table.append({'player_team': 'None', 'player_name': player.nickname})

            if league_id != '0':
                league_name = league_key(league_id).get().name
            else:
                league_name = ""

            #Send html data to browser
            template_values = {
                        'user': user.nickname(),
                        'logout_url': logout_url,
                        'team_list': team_list,
                        'Choice_key': find_Choice_key.urlsafe(), #TODO Encrypt
                        'past_choice': past_choice,
                        'event_id': event_id,
                        'update_text': update_text,
                        'league_table': league_table,
                        'league_name': league_name
                        }
            template = JINJA_ENVIRONMENT.get_template('index.html')
            self.response.write(template.render(template_values))

class UpdateInfo(webapp2.RequestHandler):


    def post(self):
        #The event_key plus the new team from the post header
        post_Choice_key = ndb.Key(urlsafe=self.request.get('Choice_key'))
        new_team = self.request.get('team')

        selection_error = isValidTeam(new_team, post_Choice_key.parent().get().league)

        #Form data into entity and submit
        post_Choice = Choice.get_or_insert(post_Choice_key.id(), parent=post_Choice_key.parent())
        if selection_error == "Good":
            post_Choice.drafted_team = int(new_team)
            str(post_Choice.put())

        #Display the homepage
        self.redirect('/?updated=' + selection_error)

application = webapp2.WSGIApplication([
                                       ('/updateuser', UpdateInfo),
                                       ('/', MainPage)
                                       ], debug=True)

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    run_wsgi_app(application)

if __name__ == "__main__":
    main()