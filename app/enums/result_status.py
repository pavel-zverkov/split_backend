from enum import Enum


class ResultStatus(Enum):
    OK = 'ok'
    DSQ = 'dsq'
    DNS = 'dns'
    DNF = 'dnf'
