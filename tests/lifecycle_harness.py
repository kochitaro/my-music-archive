"""Test-only historical controls for unchanged lifecycle engine regression cases.
Never served by the application. Production recovery paths are tested separately.
"""
import subprocess
from ui_v0322 import ROOT
BASE='6bbe6e43ae9886674e2a51d0cc0b8b43ca330164'
def controls():
 source=subprocess.check_output(['git','show',BASE+':index.html'],cwd=ROOT).decode()
 start=source.index('function mountPhotoMaintenance(){')
 end=source.index("setSection('listening');showStorageState();",start)
 # enableAfterRecovery is now supplied by the production document.
 block=source[start:end]
 start=block.index('function enableAfterRecovery()')
 end=block.index('mountPhotoMaintenance();',start)
 return block[:start]+block[end:]
