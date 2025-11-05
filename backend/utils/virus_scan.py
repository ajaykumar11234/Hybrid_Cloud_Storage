import clamd
import os

class VirusScanner:
    def __init__(self, host="localhost", port=3310):
        try:
            self.cd = clamd.ClamdNetworkSocket(host=host, port=port)
            self.cd.ping()  # test connection
        except Exception as e:
            print("⚠️ Could not connect to ClamD:", e)
            self.cd = None

    def scan_file(self, file_path):
        """Returns True if file is clean, False if infected."""
        if not self.cd:
            raise Exception("ClamD is not running or not reachable.")

        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        result = self.cd.scan(file_path)
        if not result:
            return True

        # Result example: {'/path/file.pdf': ('FOUND', 'Eicar-Test-Signature')}
        status = list(result.values())[0][0]
        return status == 'OK'
