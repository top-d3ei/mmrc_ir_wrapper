#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RH56F1 하드웨어 래퍼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
		sudo chmod 777 /dev/ttyUSB0
		python3 hand_controller.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
출력/입력 손가락 순서: 엄지벌림 엄지굽힘 검지 중지 약지 소지
모션 스텝: {'angles': [소지,약지,중지,검지,엄지굽힘,엄지벌림], 'duration': float}
"""

# from __future__ import annotations
import serial
import serial.tools.list_ports
import time
from typing import Optional

# ── 기본 설정 ─────────────────────────────────────────────────
# PORT     = '/dev/ttyUSB0'
PORT     = 'COM7'
BAUDRATE = 115200
HAND_ID  = 1

# ── 레지스터 주소 ──────────────────────────────────────────────
REG_SET_ANGLE    = 0x0410
REG_SET_POS      = 0x040A
REG_SET_SPEED    = 0x041C
REG_SET_FORCE    = 0x0416
REG_SET_MODE     = 0x044C
REG_GESTURE_NO   = 0x0870
REG_GESTURE_RUN  = 0x0872
REG_PAUSE        = 0x046A  # 일시정지: 1=정지, 0=해제

REG_GET_ANGLE    = 0x0428
REG_GET_POS      = 0x0422
REG_GET_FORCE    = 0x042E
REG_GET_CURRENT  = 0x0434
REG_GET_ERROR    = 0x043A
REG_GET_TEMP     = 0x0446
REG_GET_ANGLESET = 0x0410
REG_GET_POSSET   = 0x040A
REG_GET_SPEEDSET = 0x041C
REG_GET_FORCESET = 0x0416

# ── 각도 범위 (내부 순서: 소지 약지 중지 검지 엄지굽힘 엄지벌림) ──
ANGLE_MIN = [900,  900,  900,  900,  1100, 600 ]
ANGLE_MAX = [1740, 1740, 1740, 1740, 1350, 1800]

NUM_GESTURES  = 10  # 하드웨어에 저장된 제스처 슬롯 수


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HandController
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class RH56F1:

	# /ef __init__(self, port: str = PORT, baudrate: int = BAUDRATE, hand_id: int = HAND_ID):
	def __init__(self, baudrate: int = BAUDRATE, hand_id: int = HAND_ID):
		ports = serial.tools.list_ports.comports()
		
		portName = ""
		for p in ports:
			if ('USB Serial Port' in p.description):
				portName = p.device
				print(f"포트: {p.device} / 설명: {p.description}")

		# self._port     = port//
		self._port     = portName
		self._baudrate = baudrate
		self._hand_id  = hand_id
		self._ser: Optional[serial.Serial] = None

	# ── 연결 관리 ─────────────────────────────────

	def connect(self, port: Optional[str] = None, baudrate: Optional[int] = None) -> bool:
		"""시리얼 포트 연결"""
		if self.get_is_connected():
			self.disconnect()
		try:
			p = port     or self._port
			b = baudrate or self._baudrate

			self._ser = serial.Serial(p, b, timeout=0.05)
			self.set_speeds([1000] * 6)
			self.set_forces([500]  * 6)
			self.set_modes( [0]    * 6)
			print(f"[OK] {p} state: {self.get_is_connected()}")

			return True
		except serial.SerialException as e:
			print(f"[ERR] 연결 실패: {e}")
			return False

	def disconnect(self) -> bool:
		"""시리얼 포트 연결 해제"""
		try:
			if self._ser and self._ser.is_open:
				self._ser.close()
			return True
		except Exception as e:
			print(f"[ERR] 연결 해제 실패: {e}")
			return False

	def get_is_connected(self) -> bool:
		"""현재 연결 상태 확인"""
		return self._ser is not None and self._ser.is_open

	# ── 모션 관리 ─────────────────────────────────

	def run_motion(self, index: int) -> bool:
		"""제스처 번호(1~10) 실행. 반환: True=완료, False=오류"""
		if not self.get_is_connected():
			return False
		if not (1 <= index <= NUM_GESTURES):
			return False
		try:
			self.set_gesture(index)
			return True
		except Exception as e:
			print(f"[ERR] 모션 실행 실패: {e}")
			return False

	def stop_motion(self) -> bool:
		"""일시정지 (0x046A에 1 쓰기)"""
		if not self.get_is_connected():
			return False
		try:
			self._write(REG_PAUSE, self._to_bytes([1]))
			return True
		except Exception as e:
			print(f"[ERR] 모션 정지 실패: {e}")
			return False

	# ── 저수준 통신 ──────────────────────────────

	def _checksum(self, data):
		return sum(data) & 0xFF

	def _write(self, address, values):
		payload = [
			0xEB, 0x90,
			self._hand_id,
			len(values) + 3,
			0x12,
			address & 0xFF,
			(address >> 8) & 0xFF,
		]
		payload.extend(values)
		payload.append(self._checksum(payload[2:]))
		self._ser.write(bytes(payload))
		time.sleep(0.005)
		self._ser.read_all()

	def _read(self, address, num_bytes=12):
		"""레지스터 읽기. 반환: int 리스트 (16비트 signed)"""
		payload = [
			0xEB, 0x90,
			self._hand_id,
			0x04, 0x11,
			address & 0xFF,
			(address >> 8) & 0xFF,
			num_bytes,
		]
		payload.append(self._checksum(payload[2:]))
		self._ser.reset_input_buffer()
		self._ser.write(bytes(payload))
		time.sleep(0.02)
		recv = self._ser.read_all()
		if len(recv) < 8:
			return []
		num = (recv[3] & 0xFF) - 3
		if num <= 0 or len(recv) < 7 + num:
			return []
		raw = recv[7:7 + num]
		result = []
		for i in range(num // 2):
			v = raw[2*i] | (raw[2*i+1] << 8)
			if v > 32767:
				v -= 65536
			result.append(v)
		return result

	def _to_bytes(self, values):
		out = []
		for v in values:
			out.append(v & 0xFF)
			out.append((v >> 8) & 0xFF)
		return out

	# ── SET 명령 ─────────────────────────────────

	def set_angles(self, angles):
		"""angles: [소지, 약지, 중지, 검지, 엄지굽힘, 엄지벌림]"""
		self._write(REG_SET_ANGLE, self._to_bytes(angles))

	def set_positions(self, positions):
		"""positions: [p0~p5], 범위 0~2000"""
		self._write(REG_SET_POS, self._to_bytes(positions))

	def set_speeds(self, speeds):
		"""speeds: [s0~s5], 범위 0~4000"""
		self._write(REG_SET_SPEED, self._to_bytes(speeds))

	def set_forces(self, forces):
		"""forces: [f0~f5], 범위 0~12000"""
		self._write(REG_SET_FORCE, self._to_bytes(forces))

	def set_modes(self, modes):
			"""modes: [m0~m5] — 0=속도힘보호, 1=힘 폐루프, 2=임피던스"""
			self._write(REG_SET_MODE, self._to_bytes(modes))

	def set_gesture(self, gesture_no):
		"""사전 저장 제스처 실행. gesture_no: 1~10"""
		self._write(REG_GESTURE_NO, self._to_bytes([gesture_no]))
		time.sleep(0.005)
		self._write(REG_GESTURE_RUN, [0x01, 0x00])

	# ── GET 명령 ─────────────────────────────────

	def get_angles(self):
		"""실제 관절 각도. 반환: [소지, 약지, 중지, 검지, 엄지굽힘, 엄지벌림]"""
		return self._read(REG_GET_ANGLE)

	def get_positions(self):
		"""실제 모터 위치. 반환: [p0~p5]"""
		return self._read(REG_GET_POS)

	def get_forces(self):
		"""실제 파지력. 반환: [f0~f5]"""
		return self._read(REG_GET_FORCE)

	def get_currents(self):
		"""모터 전류. 반환: [c0~c5]"""
		return self._read(REG_GET_CURRENT)

	def get_error(self):
		"""에러 상태. 반환: [e0~e5] (0=정상)"""
		return self._read(REG_GET_ERROR)

	def get_temperature(self):
		"""내부 온도. 반환: [t0~t5]"""
		return self._read(REG_GET_TEMP)

	def get_angle_set(self):
		"""설정된 목표 각도. 반환: [소지~엄지벌림]"""
		return self._read(REG_GET_ANGLESET)

	def get_speed_set(self):
		"""설정된 속도. 반환: [s0~s5]"""
		return self._read(REG_GET_SPEEDSET)

	def get_force_set(self):
		"""설정된 파지력 한계. 반환: [f0~f5]"""
		return self._read(REG_GET_FORCESET)

	def get_touch(self):
		"""
		촉각 센서 데이터 읽기
		반환: {
			'fingers': {
				'little':  {'normal': int, 'tangential': int, 'angle': int, 'proximity': int},
				'ring':    {...}, 'middle': {...}, 'index': {...}, 'thumb': {...},
			},
			'palm': [int × 9]
		}
		"""
		payload = [self._hand_id, 0x04, 0x11, 0xB8, 0x0B, 0x44]
		cmd = bytes([0xEB, 0x90] + payload + [self._checksum(payload)])
		self._ser.reset_input_buffer()
		self._ser.write(cmd)
		time.sleep(0.03)
		recv = self._ser.read_all()

		if not recv or len(recv) < 68:
				return None

		start_idx = None
		for i in range(len(recv) - 1):
			if recv[i] == 0xB8 and recv[i+1] == 0x0B:
				start_idx = i + 2
				break
		if start_idx is None:
				return None

		fingers_order = ['little', 'ring', 'middle', 'index', 'thumb']
		finger_data = {}
		for i, name in enumerate(fingers_order):
			base = start_idx + i * 10
			if base + 9 >= len(recv):
				break
			b = recv[base:base+10]
			finger_data[name] = {
				'normal':     b[0] | (b[1] << 8),
				'tangential': b[2] | (b[3] << 8),
				'angle':      b[4] | (b[5] << 8),
				'proximity':  b[6] | (b[7] << 8) | (b[8] << 16),
			}

		palm_start = start_idx + len(fingers_order) * 10
		palm = []
		for j in range(9):
			idx = palm_start + j * 2
			if idx + 1 < len(recv):
				palm.append(recv[idx] | (recv[idx+1] << 8))

		return {'fingers': finger_data, 'palm': palm}
