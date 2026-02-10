from enum import Enum


class Privacy(Enum):
    PUBLIC = 'public'
    PRIVATE = 'private'
    FOLLOWERS = 'followers'
    BY_REQUEST = 'by_request'
