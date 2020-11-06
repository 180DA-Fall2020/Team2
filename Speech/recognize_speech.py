import random
import time

import speech_recognition as sr
import sounddevice as sd 

from scipy.io.wavfile import write

import pyaudio
import wave

from pydub import AudioSegment
from pydub.playback import play

fs = 44100
seconds = 3
chunk = 1024

def recognize_speech_from_mic(recognizer, microphone):
    """Transcribe speech from recorded from `microphone`.

    Returns a dictionary with three keys:
    "success": a boolean indicating whether or not the API request was
               successful
    "error":   `None` if no error occured, otherwise a string containing
               an error message if the API could not be reached or
               speech was unrecognizable
    "transcription": `None` if speech could not be transcribed,
               otherwise a string containing the transcribed text
    """
    # check that recognizer and microphone arguments are appropriate type
    if not isinstance(recognizer, sr.Recognizer):
        raise TypeError("`recognizer` must be `Recognizer` instance")

    if not isinstance(microphone, sr.Microphone):
        raise TypeError("`microphone` must be `Microphone` instance")

    # adjust the recognizer sensitivity to ambient noise and record audio
    # from the microphone
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    # set up the response object
    response = {
        "success": True,
        "error": None,
        "transcription": None
    }

    # try recognizing the speech in the recording
    # if a RequestError or UnknownValueError exception is caught,
    #     update the response object accordingly
    try:
        response["transcription"] = recognizer.recognize_google(audio)
    except sr.RequestError:
        # API was unreachable or unresponsive
        response["success"] = False
        response["error"] = "API unavailable"
    except sr.UnknownValueError:
        # speech was unintelligible
        response["error"] = "Unable to recognize speech"

    return response


if __name__ == "__main__":
    # set the list of words, maxnumber of guesses, and prompt limit

    # create recognizer and mic instances
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    PROMPT_LIMIT=1

    for j in range(PROMPT_LIMIT):
        print('Speak!')
        time.sleep(2)
        guess = recognize_speech_from_mic(recognizer, microphone)
        if guess["transcription"]:
            break
        if not guess["success"]:
            break
        print("I didn't catch that. What did you say?\n")

        if guess["error"]:
            print("ERROR: {}".format(guess["error"]))
            break

        # show the user the transcription
    print("You said: {}".format(guess["transcription"]))

    if str(guess["transcription"]).find("message"):
        print("What message do you want to send?") # can comment this out later
        prompt = AudioSegment.from_wav("prompt.wav") # plays audio that says "what message do you want to send"
        play(prompt)
        #record_audio()
        message = recognize_speech_from_mic(recognizer, microphone) # user speaks into mic
        print("Your message: {}".format(message["transcription"])) # playback what user said
    """else: 
        print("no message to send")
        """

