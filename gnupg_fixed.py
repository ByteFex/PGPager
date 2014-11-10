from gnupg import *

def _new_open_subprocess(self, args, passphrase=False):
    # Internal method: open a pipe to a GPG subprocess and return
    # the file objects for communicating with it.
    cmd = self.make_args(args, passphrase)
    pcmd = ' '.join(cmd)
    if self.verbose:
        print(pcmd)
    logger.debug("%s", cmd)

    # Always use shell= True to avoid problems with shell-escaped filenames!
    return Popen(pcmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)

GPG._open_subprocess= _new_open_subprocess