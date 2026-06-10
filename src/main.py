#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from InspireRobots import RH56F1
import msvcrt

def main():
    hand = RH56F1()

    print("Press Enter to connect")
    msvcrt.getch()
    # 1. 연결
    hand.connect()
    # 2. 연결 상태 확인
    print(f"연결 상태: {hand.get_is_connected()}")


    # 3. 모션 실행
    print("Press Enter to Grasp")
    msvcrt.getch()
    # hand.run_motion(1)
    hand.run_motion(2)
    # time.sleep(2)

    # 4. 모션 재실행 후 정지
    print("Press Enter to Release")
    msvcrt.getch()
    hand.run_motion(1)
    # time.sleep(0.5)

    print("Press Enter to Stop")
    msvcrt.getch()
    hand.stop_motion()

    print("Press Enter to disconnect")
    msvcrt.getch()
    # 5. 연결 해제
    hand.disconnect()

    # 6. 연결 상태 확인
    print(f"연결 상태: {hand.get_is_connected()}")

if __name__ == '__main__':
    main()