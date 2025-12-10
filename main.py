from sim import Simulation
from viz2d import run_live_viz


def main():
    sim = Simulation()
    sim.build()
    print(
        "Starting simulation in 2D "
        "(simplified MAC, secure-ish handshake, DV cost labels + aging, DV dest cycling)"
    )
    run_live_viz(sim)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
