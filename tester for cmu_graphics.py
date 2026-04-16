from cmu_graphics import *
import random
import threading

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

latest = {
    'alpha': None,
    'beta': None,
    'hsi': None
} #where livestream stores data

#automatically called and stores new alpha/beta calues
def alpha_handler(address, *args):
    latest['alpha'] = args

def beta_handler(address, *args):
    latest['beta'] = args

def hsi_handler(address, *args):
    latest['hsi'] = args        
#up to here
def all_handler(address, *args):
    print("RECEIVED:", address, args)
#start server ..?
def startMuseServer():
    dispatcher = Dispatcher()
    dispatcher.map("/muse/elements/alpha_absolute", alpha_handler)
    dispatcher.map("/muse/elements/beta_absolute", beta_handler)
    dispatcher.map("/muse/elements/horseshoe", hsi_handler)
    dispatcher.set_default_handler(all_handler)  # optional, for debugging prints

    server = BlockingOSCUDPServer(("0.0.0.0", 5000), dispatcher)
    print("Listening on port 5000...")
    server.serve_forever()
#turn eeg data --> valence and arousal
def getMuseEmotion():
    if latest['alpha'] is None or latest['beta'] is None:
        return None

    alpha = latest['alpha'][0]
    beta = latest['beta'][0]

    arousalRaw = beta / (alpha + 0.001)
    arousal = max(0, min(1, (arousalRaw - 0.8) / 1.5))

    valence = 0
    return valence, arousal

def onAppStart(app):
    app.steps = 0
    app.valence = 0
    app.arousal = 0
    app.particles = []
    for _ in range(80):
        app.particles.append(makeParticle(app))
    app.museThread = threading.Thread(target=startMuseServer, daemon=True)
    app.museThread.start()

        
def getColorFromValence(valence):
    t = (valence + 1) / 2 # map [-1,1] → [0,1]
    r = 255
    g = int(255 * t)
    b = 0
    return rgb(r, g, b)


def redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='black')
    status = "LIVE" if latest['alpha'] is not None else "WAITING"
    drawLabel(status, 60, 20, fill='white')
    
    for p in app.particles:
        color = getColorFromValence(app.valence)
        drawCircle(p['x'], p['y'], p['r'], fill=color, opacity=60)
    
    drawLabel(f'Valence: {app.valence:.2f}', app.width-80, 20, fill='white', align = 'left')
    drawLabel(f'Arousal: {app.arousal:.2f}', app.width-80, 40, fill='white', align = 'left')

def makeParticle(app):
    return {
        'x': random.uniform(0, app.width),
        'y': random.uniform(0, app.height),
        'dx': random.uniform(-2, 2),
        'dy': random.uniform(-2, 2),
        'r': random.uniform(2, 6)
        }

def updateEmotions(app):
    museEmotion = getMuseEmotion()

    if museEmotion is not None:
        newValence, newArousal = museEmotion

        app.valence = 0.9 * app.valence + 0.1 * newValence
        app.arousal = 0.9 * app.arousal + 0.1 * newArousal
    
def onStep(app):
    app.steps += 1
    updateEmotions(app)
    updateParticles(app)
    
def updateParticles(app):
    jitter = .5 + 6*app.arousal #jitter is linked to arousal
    drift = 1.5 * app.valence #direction it moves
    for p in app.particles:
        p['x'] += p['dx'] + random.uniform(-jitter, jitter)
        p['y'] += p['dy'] + random.uniform(-jitter, jitter) - drift #drift alr linked to valence, up/down

        if p['x'] < 0: p['x'] = app.width
        if p['x'] > app.width: p['x'] = 0
        if p['y'] < 0: p['y'] = app.height
        if p['y'] > app.height: p['y'] = 0
    

def main():
    runApp()
main()