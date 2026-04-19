from cmu_graphics import *
import numpy as np
import sounddevice as sd 
import random
#imports below are from AI
import threading #lets Muse server run in background

from pythonosc.dispatcher import Dispatcher 
#dispatcher tells u what handler (alpha, beta, etc) to call
#similar to how runApp auto calls onAppStart, redrawAll, onStep
from pythonosc.osc_server import BlockingOSCUDPServer
#from AI
latest = {
    'alpha': None,
    'beta': None,
    'hsi': None
} #where livestream stores data

#all from AI; automatically called and stores new alpha/beta calues
def alpha_handler(address, *args):
    latest['alpha'] = args

def beta_handler(address, *args):
    latest['beta'] = args

def hsi_handler(address, *args):
    latest['hsi'] = args        

def all_handler(address, *args):
    pass
    #print("RECEIVED:", address, args)
#from AI; start server 
def startMuseServer():
    dispatcher = Dispatcher()
    dispatcher.map("/muse/elements/alpha_absolute", alpha_handler)
    dispatcher.map("/muse/elements/beta_absolute", beta_handler)
    dispatcher.map("/muse/elements/horseshoe", hsi_handler)
    dispatcher.set_default_handler(all_handler)  # optional, for debugging prints

    server = BlockingOSCUDPServer(("0.0.0.0", 5000), dispatcher)
    print("Listening on port 5000...")
    server.serve_forever()
#from AI; turn eeg data --> valence and arousal
def getMuseEmotion():
    if latest['alpha'] is None or latest['beta'] is None:
        return None

    alpha = latest['alpha']
    beta = latest['beta']
    #print("alpha:", latest['alpha'])
    #print("beta:", latest['beta'])  
    if len(alpha) < 4 or len(beta) < 4: 
        #basically if ur getting less than 4 arguments,
        #return None and skip getting the emotion for now. 
        #(in updateEmotions, if it's None, nothing changes; val/arousal same.)
        return None

    AF7 = 1
    AF8 = 2

    alphaAF7 = alpha[AF7]
    alphaAF8 = alpha[AF8]
    betaAF7 = beta[AF7]
    betaAF8 = beta[AF8]

    # AROUSAL (standard)
    alphaAvg = (alphaAF7 + alphaAF8) / 2
    betaAvg = (betaAF7 + betaAF8) / 2
    arousalRaw = betaAvg / (alphaAvg + 0.001)
    arousal = max(0, min(1, (arousalRaw - 0.9) / 0.8))

    # VALENCE (real method)
    valenceRaw = alphaAF8 - alphaAF7

    # scale it (IMPORTANT — raw values are big)
    valence = max(-1, min(1, valenceRaw * 0.75))

    return valence, arousal
def onAppStart(app):
    app.frequency = 200
    app.amplitude = 0.6
    app.mySound = sine_tone(app.frequency, 1, app.amplitude)
    app.steps = 0
    app.valence = 0
    app.arousal = 0
    app.particles = []
    for _ in range(80):
        app.particles.append(makeParticle(app))
    app.museThread = threading.Thread(target=startMuseServer, daemon=True)
    app.museThread.start()
    app.arousalHistory = []
    app.valenceHistory = []
    app.maxPoints = 200   # how many points to keep on screen
#from AI     
def getColorFromValence(valence):
    valence = max(-1, min(1, valence * 6)) #scale it more
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
    drawGraphs(app)

def drawGraphs(app):
    # graph settings
    graphWidth = 300
    graphHeight = 100
    margin = 20

    # positions
    x0 = margin
    y0 = app.height - graphHeight - margin

    # draw background
    drawRect(x0, y0, graphWidth, graphHeight, fill=None, border='white')
    drawRect(x0 + 340, y0, graphWidth, graphHeight, fill=None, border='white')

    # labels
    drawLabel("Arousal", x0 + 40, y0 - 10, fill='white')
    drawLabel("Valence", x0 + 360, y0 - 10, fill='white')

    # spacing between points
    if len(app.arousalHistory) > 1:
        dx = graphWidth / len(app.arousalHistory)

        # draw arousal (left graph)
        for i in range(len(app.arousalHistory) - 1):
            x1 = x0 + i * dx
            x2 = x0 + (i + 1) * dx

            y1 = y0 + graphHeight * (1 - app.arousalHistory[i])
            y2 = y0 + graphHeight * (1 - app.arousalHistory[i + 1])

            drawLine(x1, y1, x2, y2, fill='cyan')

        # draw valence (right graph, shifted right)
        offset = graphWidth + 40

        for i in range(len(app.valenceHistory) - 1):
            x1 = x0 + offset + i * dx
            x2 = x0 + offset + (i + 1) * dx

            # valence is [-1,1] → map to [0,1]
            v1 = (app.valenceHistory[i] + 1) / 2
            v2 = (app.valenceHistory[i + 1] + 1) / 2

            y1 = y0 + graphHeight * (1 - v1)
            y2 = y0 + graphHeight * (1 - v2)

            drawLine(x1, y1, x2, y2, fill='yellow')

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

        app.valence = 0.9 * app.valence + 0.1 * newValence #smoothing
        app.arousal = 0.7 * app.arousal + 0.3 * newArousal
      
def onStep(app):
    app.steps += 1
    
    updateEmotions(app)
    updateParticles(app)
    updateSoundProperties(app)
    if app.steps % 50 == 0:
        sd.play(app.mySound)

        # store history
    app.arousalHistory.append(app.arousal)
    app.valenceHistory.append(app.valence)

    # keep list from getting too long
    if len(app.arousalHistory) > app.maxPoints:
        app.arousalHistory.pop(0)
        app.valenceHistory.pop(0)

def updateSoundProperties(app):
    app.frequency = 200+200*app.arousal
    app.amplitude = app.arousal
    sines = [sine_tone(frequency = 200 + 200*app.arousal, amplitude = 0.7/(1+app.amplitude)) for i in range(1,31,2)]
    #app.mySound = sine_tone(app.frequency, 1, app.amplitude)
    app.mySound = sum(sines)
    
    
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

#from here on: AUDIO    
def sine_tone(
        frequency: int = 200,
        duration: float = 1.0,
        amplitude: float = 0.5,
        sample_rate: int=44100
        ) -> np.ndarray:
    n_samples = int(sample_rate * duration)
    #make sequence of time pts. generate array of evenly spaced vals
    #range is 0 to duration, length is n samples,false means endpoint excluded
    time_points = np.linspace(0, duration, n_samples, False)
    #make sine wave. .sin() takes in angle in radians.
    #frequency in hz --> radians per second (angular freq), using 2pi * frequency
    #then, we get angular position, or phase of the wave for each time pt
    sine = np.sin(2*np.pi*frequency * time_points)
    sine *= amplitude
    return sine

def main():
    runApp()
    


main()