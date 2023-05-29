import os.path as osp

from scheduler import generate_rotation
from generate_rotation import PI8
from helpers.layer_approach_related_files import plot_placement_results


def get_ticks_where_ms_waiting_for_pi8(
    ms_available_at_end_of_tick: dict[int, set[int]],
    scheduling_results: dict[int, dict[int, int]],
    rotation_ids: dict[int, tuple[int, list[int]]],
) -> set[int]:
    """For each tick, check if there are any m.s.
    available where no pi8 rotations are scheduled for
    the tick. This implies that the m.s. are waiting
    for a pi8 rotation, which is blocked by a pi4
    rotation. All rotations after the last pi8
    rotation are excluded.
    """
    waiting = set()
    last_pi8_tick = get_last_pi8_tick(scheduling_results, rotation_ids)
    for tick, rotation_and_ms in scheduling_results.items():
        if ms_available_at_end_of_tick[tick] and tick < last_pi8_tick:
            for rotation_ind in rotation_and_ms:
                if rotation_ids[rotation_ind][0] == PI8:
                    break
            else:
                waiting.add(tick)

    return waiting


def get_ticks_where_pi8_waiting_for_ms(
    ms_available_at_start_of_tick: dict[int, set[int]],
    first_layer_at_start_of_tick: dict[int, list[int]],
    rotation_ids: dict[int, tuple[int, list[int]]],
) -> set[int]:
    """Check for ticks where all rotations in first layer
    are pi8, but no magic state is available at the start of
    the tick.
    """
    waiting = set()
    for tick, first_layer in first_layer_at_start_of_tick.items():
        if not ms_available_at_start_of_tick[tick]:
            for rotation_ind in first_layer:
                if rotation_ids[rotation_ind][0] != PI8:
                    break
            else:
                waiting.add(tick)

    return waiting


def get_last_pi8_tick(
    scheduling_results: dict[int, dict[int, int]],
    rotation_ids: dict[int, tuple[int, list[int]]],
) -> int:
    """Check for the tick at which last pi8 rotation is scheduled.
    We want to exclude all rotations after this for our metrics
    """

    pi8s = []
    for tick, rot_and_ms in scheduling_results.items():
        for rot_id in rot_and_ms:
            if rotation_ids[rot_id][0] == PI8:
                pi8s.append(tick)
                break

    assert len(pi8s) > 0, "This code doesn't work if there are no pi8 rotations"
    last_pi8_tick = max(pi8s)
    return last_pi8_tick


def get_idling_metrics(scheduling_results: list[dict]) -> list[list[int]]:
    """scheduling_results is a list of dicts.
    The dict contains the following:

    "total_ticks": int
    "rotation_schedule": dict[int, dict[int, int]]
    "solve_time": float
    "ms_avialable_tick_start": dict[int, set[int]]
    "ms_avialable_tick_end": dict[int, set[int]]
    "first_layer_tick_start": dict[int, list[int]]
    "first_layer_tick_end": dict[int, list[int]]
    "rotation_IDs": dict[int, tuple[int, list[int]]]

    Returns:
        pi8_waiting_ms_all: list[list[int]]
            A list of multiple lists of all ticks
            where pi8 rotations are waiting for magic states

        ms_waiting_pi8_all: list[list[int]]
            A list of multiple lists of all ticks
            where magic states are waiting for pi8 rotations

        Note: multiple lists since we test N placements
    """

    pi8_waiting_ms_all = []
    ms_waiting_pi8_all = []

    for result in scheduling_results:
        pi8_waiting_ms_all.append(
            get_ticks_where_pi8_waiting_for_ms(
                result["ms_available_tick_start"],
                result["first_layer_tick_start"],
                result["rotation_IDs"],
            )
        )

        ms_waiting_pi8_all.append(
            get_ticks_where_ms_waiting_for_pi8(
                result["ms_available_tick_end"],
                result["rotation_schedule"],
                result["rotation_IDs"],
            )
        )

    return pi8_waiting_ms_all, ms_waiting_pi8_all


if __name__ == "__main__":
    """Used to print idling metrics after experiments"""

    scheduling_results_path = plot_placement_results.find_relevant_files_in_output(
        ".pkl"
    )

    if scheduling_results_path:
        for path in scheduling_results_path:
            scheduling_results = generate_rotation.load_var(path)

            pi8_waiting_ms_all, ms_waiting_pi8_all = get_idling_metrics(
                scheduling_results
            )

            print("Metrics for " + str(osp.basename(path)))

            for pi8_waiting_ms, ms_waiting_pi8 in zip(
                pi8_waiting_ms_all, ms_waiting_pi8_all
            ):
                print("Num ticks PI8 waiting for M.S: " + str(len(pi8_waiting_ms)))

                print(
                    "Num ticks M.S. waiting for PI8: " + str(len(ms_waiting_pi8)) + "\n"
                )

            print("*" * 65)
    else:
        print(
            "No experiment files found in the directory "
            "Trillium/output. Please run experiments first."
        )
