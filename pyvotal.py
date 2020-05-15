import re
import json
from datetime import datetime
import urllib.request
import urllib.parse
import itertools
from functools import reduce

# story types
CHORE = "chore"
BUG = "bug"
FEATURE = "feature"

# story states
UNSCHEDULED = "unscheduled"
UNSTARTED = "unstarted"
STARTED = "started"
FINISHED = "finished"
DELIVERED = "delivered"
REJECTED = "rejected"
ACCEPTED = "accepted"

api_base = "https://www.pivotaltracker.com/services/v5/"
token = None

def set_token(t):
    global token
    token = t

def parse_date(date_str):
    curr = None
    try:
        curr = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    except:
        pass
    if curr is None:
        print("Possibly invalid date format: %s" % date_str)
    return curr

class UnknownPropertyException(Exception):
    pass

class NoTokenException(Exception):
    pass

class Base():
    json = None

    def __init__(self, json):
        self.json = json

    def __getattr__(self, attr):
        if attr in self.json.keys(): 
            return self.json[attr]
        raise UnknownPropertyException("%s has no attribute '%s'" % (self.__class__.__name__, attr))

    @staticmethod
    def fetch(path, parser=None):
        if not token:
            raise NoTokenException('No token had been set!')
        opener = urllib.request.build_opener()
        opener.addheaders = [('X-TrackerToken', token)]
        urllib.request.install_opener(opener)
        response = urllib.request.urlopen(api_base + path).read()
        json_object = json.loads(response.decode('utf-8'))
        return json_object if parser is None else parser(json_object)

class Project(Base):
    _epics = None

    def epics(self):
        if self._epics is None:
            self._epics = Epic.fetch_all(self.id)
        return self._epics

    @staticmethod
    def fetch_all():
        return Project.fetch('projects', lambda ps: [Project(p) for p in ps])

class Epic(Base):
    _priority = None
    _stories = None
    _activities = None
    _label = None

    def __init__(self, priority, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._priority = priority

    def __getattr__(self, attr):
        if attr in ['priority']:
            return self._priority
        if attr in ['created_at', 'updated_at']:
            return parse_date(self.json[attr])
        if attr in ['label']:
            if self._label is None:
                self._label = Label(self.json['label'])
            return self._label
        if attr in ['stories']:
            if self._stories is None:
                self._stories = Story.fetch_all(self.project_id, self.label.name)
            return self._stories
        if attr in ['activities']:
            if self._activities is None:
                self._activities = Activity.fetch_all(self.project_id, self.id)
            return self._activities
        return super().__getattr__(attr)

    def get_estimate(self):
        total = 0
        ongoing = 0
        accepted = 0

        # Note: we aren't consurned about unscheduled (I.e. iceboxed) stories
        for s in self.stories:
            if not s.is_feature():
                continue
            k = s.current_state
            if k != UNSCHEDULED:
                total = total + s.get_points()
            if k in [STARTED, FINISHED, DELIVERED]:
                ongoing = ongoing + s.get_points()
            if k == ACCEPTED:
                accepted = accepted + s.get_points()

        return (total, ongoing, accepted)

    def get_most_recent_estimate(self):
        if self.engman_data is None or 'estimates' not in self.engman_data.keys():
            return None

        est = 0
        curr = datetime.strptime("1982-05-03 23:00", "%Y-%m-%d %H:%M") #random old date
        for estimate in self.engman_data['estimates']:
            est_date = Epic.parse_date(estimate['datetime'])
            if curr < est_date:
                est = estimate['size']
                curr = est_date

        return est

    def get_launch(self):
        if self.engman_data is None or 'launch' not in self.engman_data.keys():
            return None
        return self.parse_date(self.engman_data['launch'])

    @staticmethod
    def fetch_all(project_id):
        """Fetches all epics in project"""
        return Epic.fetch('projects/' + str(project_id) + '/epics', lambda es: [Epic(i + 1, e) for i, e in enumerate(es)])

    def has_outstanding_stories(self, story_fetcher):
        self.ensure_stories_loaded(story_fetcher)
        for s in self.stories:
            if s.get_state() not in [UNSCHEDULED, ACCEPTED]:
                return True

    def get_story_distribution(self):

        stats = {}
        stats[UNSCHEDULED] = 0
        stats[UNSTARTED] = 0
        stats[STARTED] = 0
        stats[FINISHED] = 0
        stats[DELIVERED] = 0
        stats[REJECTED] = 0
        stats[ACCEPTED] = 0
        
        for s in self.stories:
            stats[s.current_state] = stats[s.current_state] + 1

        return stats

    def get_links(self):
        if self.engman_data is None or 'links' not in self.engman_data.keys():
            return None
        return [ "%s: %s" % (name, self.engman_data['links'][name]) for name in self.engman_data['links']]

class Activity(Base):
    _person = None

    @staticmethod
    def fetch_all(project_id, epic_id):
        endpoint = '/projects/%s/epics/%s/activity' % (project_id, epic_id)
        return Activity.fetch(endpoint, lambda aa: [Activity(a) for a in aa])

    def __getattr__(self, attr):
        if attr in ['performed_by']:
            if self._person is None:
                self._person = Person(super().__getattr__('performed_by'))
            return self._person
        return super().__getattr__(attr)

class Person(Base):
    pass

class Label(Base):
    pass

class Story(Base):
    def __getattr__(self, attr):
        if attr in ['accepted_at']:
            return parse_date(self.json[attr])
        return super().__getattr__(attr)

    @staticmethod
    def fetch_all(project_id, epic_label):
        endpoint = 'projects/%s/stories?with_label=%s' % (str(project_id), urllib.parse.quote(epic_label))
        return Story.fetch(endpoint, lambda ss: [Story(s) for s in ss])

    def is_active(self):
        pass

    def get_points(self):
        return self.estimate if self.has_estimate() else 0

    def is_chore(self):
        return self.story_type == CHORE

    def is_bug(self):
        return self.story_type == BUG

    def is_feature(self):
        return self.story_type == FEATURE

    def has_estimate(self):
        return 'estimate' in self.json.keys()
