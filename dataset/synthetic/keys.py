import warnings
from typing import Iterator, Tuple, List, Dict, Any, Iterable
from pathlib import Path

from config import OUTPUT_DIR, DEFAULT_SOUNDFONT_LOCATION
from dataset.synthetic.dataset_writer import DatasetWriter, DatasetRowDescription
from dataset.music.transforms import get_tonic_midi_note_value, get_scale
from dataset.music.constants import PITCH_CLASS_TO_NOTE_NAME_SHARP
from dataset.music.midi import (
    create_midi_file,
    create_midi_track,
    write_melody,
)
from dataset.audio.synth import produce_synth_wav_from_midi
from dataset.audio.wav import is_wave_silent

# Play style definitions
_PLAY_STYLE = {
    0: "ASCENDING",
    1: "DESCENDING",
}

def get_all_keys() -> List[Tuple[int, str]]:
    return [
        (note, "ionian")
        for note in PITCH_CLASS_TO_NOTE_NAME_SHARP.values()
    ]

def get_single_instrument() -> List[Dict[str, Any]]:
    """Return only one instrument."""
    return [
        {"program": 0, "name": "Acoustic Grand Piano", "category": "Piano"}
    ]

def get_key_midi(
    root_note: str, mode: str, play_style: int, include_octave_above: bool = True,
):
    pitch_classes = get_scale(root_note, mode)
    midi_tonic_val = get_tonic_midi_note_value(pitch_classes[0])

    # Fix offset calculation to stay in same octave
    offsets = [(n - pitch_classes[0]) % 12 for n in pitch_classes]

    if include_octave_above:
        offsets.append(12)

    notes = [midi_tonic_val + offset for offset in offsets]

    if play_style == 1:
        notes.reverse()

    time_per_note = 1
    timed_notes = []
    prev_beat = 0
    for n in notes:
        start_beat = prev_beat
        end_beat = start_beat + time_per_note
        timed_notes.append((start_beat, end_beat, (n, None)))
        prev_beat = end_beat

    return timed_notes

def get_row_iterator(
    keys: Iterable[Tuple[str, str]],
    instruments: List[Dict[str, Any]],
) -> Iterator[DatasetRowDescription]:
    idx = 0
    for root_note, mode in keys:
        for play_style, play_style_name in _PLAY_STYLE.items():
            for instrument_info in instruments:
                yield (
                    idx,
                    {
                        "instrument_info": instrument_info,
                        "play_style": play_style,
                        "play_style_name": play_style_name,
                        "root_note": root_note,
                        "mode": mode,
                    }
                )
                idx += 1

def row_processor(
    dataset_path: Path, row: DatasetRowDescription
) -> List[DatasetRowDescription]:
    row_idx, row_info = row
    play_style = row_info["play_style"]
    play_style_name = row_info["play_style_name"]
    root_note = row_info["root_note"]
    mode = row_info["mode"]

    instrument_info = row_info["instrument_info"]
    midi_program_num = instrument_info["program"]
    midi_program_name = instrument_info["name"]
    midi_category = instrument_info["category"]

    cleaned_name = midi_program_name.replace(" ", "_")
    midi_file_path = dataset_path / f"{root_note}_{mode}_{play_style_name}_{midi_program_num}_{cleaned_name}.mid"
    synth_file_path = dataset_path / f"{root_note}_{mode}_{play_style_name}_{midi_program_num}_{cleaned_name}.wav"

    scale_midi = get_key_midi(root_note, mode, play_style)
    midi_file = create_midi_file()
    midi_track = create_midi_track(
        bpm=120,
        time_signature=(4, 4),
        key_root=root_note,
        track_name=midi_program_name,
        program=midi_program_num,
        channel=2,
    )
    write_melody(scale_midi, midi_track, channel=2)
    midi_file.tracks.append(midi_track)
    midi_file.save(midi_file_path)
    produce_synth_wav_from_midi(midi_file_path, synth_file_path)
    is_silent = is_wave_silent(synth_file_path)

    return [
        (
            row_idx,
            {
                "key_root_note": root_note,
                "key_mode": mode,
                "play_style": play_style_name,
                "midi_program_num": midi_program_num,
                "midi_program_name": midi_program_name,
                "midi_category": midi_category,
                "midi_file_path": str(midi_file_path.relative_to(dataset_path)),
                "synth_file_path": str(synth_file_path.relative_to(dataset_path)),
                "synth_soundfont": DEFAULT_SOUNDFONT_LOCATION.parts[-1],
                "is_silent": is_silent,
            },
        )
    ]
    
if __name__ == "__main__":
    dataset_name = "keys_new"
    dataset_writer = DatasetWriter(
        dataset_name=dataset_name,
        save_to_parent_directory=OUTPUT_DIR,
        row_iterator=get_row_iterator(
            keys=get_all_keys(),
            instruments=get_single_instrument(),  
        ),
        row_processor=row_processor,
        max_processes=4,  # Lower processes if small dataset
    )

    dataset_df = dataset_writer.create_dataset()

    num_silent_samples = dataset_df[dataset_df["is_silent"] == True].shape[0]
    if num_silent_samples > 0:
        warnings.warn(
            f"In the dataset, there were {num_silent_samples} silent samples.",
            UserWarning,
        )
