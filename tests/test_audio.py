import pytest

from ulac import audio


def test_music_must_be_instrumental_and_never_vocal():
    assert audio.music_problems("gentle instrumental felt piano and celesta, no vocals") == []
    assert audio.music_problems("gentle felt piano") == ["music prompt must say instrumental"]
    assert "voice" in " ".join(audio.music_problems("instrumental with a soft female voice"))
    with pytest.raises(ValueError):
        audio.ace_step_15("pop song with singing", seconds=30, bpm=90, keyscale="F major", prefix="x")


def test_ace_graph_is_instrumental_flac_and_sfx_refuses_music_and_voice():
    g = audio.ace_step_15("instrumental felt piano, celesta, no vocals", seconds=38.5, bpm=84, keyscale="F major", prefix="x")
    assert g["94"]["inputs"]["lyrics"] == "[Instrumental]" and g["107"]["inputs"]["format"] == "flac"
    assert g["98"]["inputs"]["seconds"] == 38.5
    assert audio.sfx_problems("wax crayon scratching on paper, close, no music") == []
    assert audio.sfx_problems("a cheerful melody") and audio.sfx_problems("a child humming")
    with pytest.raises(ValueError):
        audio.eleven_sfx("background music", seconds=3, prefix="x")
    assert audio.estimate("sonilo", 40) == 16.0 and audio.estimate("ace15", 40) == 0.0 and audio.estimate("sfx", 4) == 2.0
