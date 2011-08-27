/*
 * Basic python interface to do a ReplayGain analysis.
 */
#include <Python.h>
#include <sndfile.h>

#include "gain_analysis.h"

static PyObject *GainError;
static Float_t album_peak;

static PyObject *
gain_clear(PyObject *self, PyObject *args)
{
    int err;

    /* This sample frequency is arbitrary since it will be reset
     * before each song is analyzed. */
    err = InitGainAnalysis(44100);
    if (err != INIT_GAIN_ANALYSIS_OK) {
        PyErr_SetString(GainError, "Error clearing ReplayGain data");
        return NULL;
    }

    album_peak = 0.0;

    Py_RETURN_NONE;
}

static PyObject *
gain_track(PyObject *self, PyObject *args)
{
    int fd, read_err, process_err;
    Float_t track_gain, track_peak = -1.0;
    SNDFILE* handle;
    SF_INFO info;

    if (!PyArg_ParseTuple(args, "i", &fd))
        return NULL;

    info.format = 0;
    Py_BEGIN_ALLOW_THREADS
    handle = sf_open_fd(fd, SFM_READ, &info, 0);
    Py_END_ALLOW_THREADS
    if (handle == NULL) {
        PyErr_SetString(GainError, sf_strerror(NULL));
        return NULL;
    }

    process_err = ResetSampleFrequency(info.samplerate);
    if (process_err != INIT_GAIN_ANALYSIS_OK) {
        PyErr_SetString(GainError, "Invalid sample rate");
        sf_close(handle);
        return NULL;
    }

    read_err = 0;
    process_err = GAIN_ANALYSIS_OK;
    Py_BEGIN_ALLOW_THREADS
    while (1) {
        sf_count_t frames = 1024;
        short buf_src[frames][info.channels];
        Float_t buf_dst[2][frames];

        frames = sf_readf_short(handle, (short*)buf_src, frames);
        if (frames <= 0) {
            read_err = frames;
            break;
        }

        /* The ReplayGain library uses Float_t for its API which is
         * actually a double and the data stored is 16bit PCM, not
         * floating point data... All I have to say is wow... */
        if (info.channels >= 2) {
            for (int f = 0; f < frames; f++) {
                for (int c = 0; c < 2; c++) {
                    buf_dst[c][f] = (Float_t)buf_src[f][c];
                    if (buf_dst[c][f] > track_peak)
                        track_peak = buf_dst[c][f];
                }
            }
            process_err = AnalyzeSamples(buf_dst[0], buf_dst[1], frames, 2);
        }
        else {
            for (int f = 0; f < frames; f++) {
                buf_dst[0][f] = (Float_t)buf_src[f][0];
                if (buf_dst[0][f] > track_peak)
                    track_peak = buf_dst[0][f];
            }
            process_err = AnalyzeSamples(buf_dst[0], NULL, frames, 1);
        }
        if (process_err != GAIN_ANALYSIS_OK)
            break;
    }
    Py_END_ALLOW_THREADS

    if (read_err < 0) {
        PyErr_SetString(GainError, sf_strerror(handle));
        sf_close(handle);
        return NULL;
    }

    if (sf_close(handle)) {
        PyErr_SetString(GainError, sf_strerror(handle));
        return NULL;
    }

    if (process_err != GAIN_ANALYSIS_OK) {
        PyErr_SetString(GainError, "Error in ReplayGain analysis");
        return NULL;
    }

    track_gain = GetTitleGain();
    if (track_gain == GAIN_NOT_ENOUGH_SAMPLES) {
        PyErr_SetString(GainError,
                        "Not enough samples for ReplayGain analysis");
        return NULL;
    }

    track_peak = track_peak / 32767.0;
    if (track_peak > album_peak)
        album_peak = track_peak;

    return Py_BuildValue("dd", (double)track_gain, (double)track_peak);
}

static PyObject *
gain_album(PyObject *self, PyObject *args)
{
    Float_t album_gain;

    if (!PyArg_ParseTuple(args, ""))
        return NULL;

    album_gain = GetAlbumGain();
    if (album_gain == GAIN_NOT_ENOUGH_SAMPLES) {
        PyErr_SetString(GainError,
                        "Not enough samples for ReplayGain analysis");
        return NULL;
    }

    return Py_BuildValue("dd", (double)album_gain, (double)album_peak);
}

static PyMethodDef gain_methods[] = {
    {"clear", gain_clear, METH_VARARGS, "Clear ReplayGain state."},
    {"track", gain_track, METH_VARARGS,
        "Analyze and return ReplayGain for a single track."},
    {"album", gain_album, METH_VARARGS,
        "Finish analysis and return ReplayGain for all tracks."},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
init_gain(void)
{
    PyObject *m, *reference;

    m = Py_InitModule("_gain", gain_methods);
    if (m == NULL)
        return;

    GainError = PyErr_NewException("_gain.GainError", NULL, NULL);
    Py_INCREF(GainError);
    PyModule_AddObject(m, "GainError", GainError);

    reference = Py_BuildValue("d", ReplayGainReferenceLoudness);
    PyModule_AddObject(m, "REFERENCE_LOUDNESS", reference);
}
