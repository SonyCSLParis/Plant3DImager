// ===================================================================
// Simultaneous control of 2 stepper motors with Adafruit Motor FeatherWing
// Version with LIMIT SWITCH for TILT homing only
// ===================================================================

#include <Wire.h>
#include <Adafruit_MotorShield.h>

Adafruit_MotorShield AFMS = Adafruit_MotorShield();

// ==================== MOTORS ====================
// Motor 1 = PAN (horizontal rotation) with 5:1 reduction
Adafruit_StepperMotor *motor1 = AFMS.getStepper(400, 1);
const float stepAngle1 = 0.9;
const float reductionRatio1 = 5.0;

// Motor 2 = TILT (vertical inclination) without reduction
Adafruit_StepperMotor *motor2 = AFMS.getStepper(400, 2);
const float stepAngle2 = 0.9;

// ==================== LIMIT SWITCH FOR TILT HOMING ====================
#define LIMIT_SWITCH_PIN 10  // Digital pin for limit switch
// Wiring: Pin 10 → NO switch terminal 1
//         GND    → NO switch terminal 2

// Offset to apply after limit switch detection (in degrees)
// Positive value = FORWARD rotation (clockwise)
// Negative value = BACKWARD rotation (counter-clockwise)
float TILT_HOMING_OFFSET = 0.0;

// Homing parameters
const int HOMING_SPEED_RPM = 5;               // Slow speed for precision
const unsigned long HOMING_TIMEOUT = 20000;   // 20 seconds max

// ==================== STATE VARIABLES ====================
bool emergencyStop = false;
bool isMoving = false;
bool isHomed = false;


// ==================== INITIALIZATION ====================
void setup() {
  Serial.begin(9600);
  while (!Serial);  // Wait for serial port to be ready
  
  Serial.println("=== Gimbal Control System ===");
  Serial.println("Initializing Motor Shield...");
  AFMS.begin();
  
  // Configure limit switch with internal pull-up
  pinMode(LIMIT_SWITCH_PIN, INPUT_PULLUP);
  Serial.print("Limit switch configured on pin ");
  Serial.println(LIMIT_SWITCH_PIN);
  
  // Configure normal motor speeds
  motor1->setSpeed(30);  // RPM for PAN
  motor2->setSpeed(30);  // RPM for TILT
  
  // Display available commands
  Serial.println("\n=== Available Commands ===");
  Serial.println("  '<angle_pan> <angle_tilt>' : Rotate motors (ex: 10 -5)");
  Serial.println("  'HOME'                     : Start TILT homing");
  Serial.println("  'OFFSET <value>'           : Set homing offset (ex: OFFSET 5.0)");
  Serial.println("  'STOP'                     : Emergency stop");
  Serial.println("\nNote: Motor 1 (PAN) has a 5:1 reduction ratio");
  Serial.println("System ready.\n");
}


// ==================== MAIN LOOP ====================
void loop() {
  static String inputString = "";
  
  // Read from serial port
  while (Serial.available()) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (inputString.length() > 0) {
        
        // ===== STOP COMMAND =====
        if (inputString.equalsIgnoreCase("STOP")) {
          emergencyStop = true;
          motor1->release();
          motor2->release();
          isMoving = false;
          Serial.println(">>> EMERGENCY STOP ACTIVATED <<<");
        }
        
        // ===== HOME COMMAND =====
        else if (inputString.equalsIgnoreCase("HOME")) {
          performHoming();
        }
        
        // ===== OFFSET COMMAND =====
        else if (inputString.startsWith("OFFSET ")) {
          String offsetStr = inputString.substring(7);
          float newOffset = offsetStr.toFloat();
          TILT_HOMING_OFFSET = newOffset;
          Serial.print("Homing offset set to ");
          Serial.print(TILT_HOMING_OFFSET);
          Serial.println(" degrees");
        }
        
        // ===== MOVEMENT COMMAND =====
        else {
          emergencyStop = false;
          processCommand(inputString);
        }
        
        inputString = "";
      }
    } else {
      inputString += c;
    }
  }
}


// ==================== TILT HOMING FUNCTION ====================
void performHoming() {
  Serial.println("\n=== STARTING TILT HOMING ===");
  
  // --- STEP 1: Initial limit switch check ---
  if (digitalRead(LIMIT_SWITCH_PIN) == LOW) {
    Serial.println("WARNING: Limit switch already triggered");
    Serial.println("Moving away from switch...");
    
    motor2->setSpeed(HOMING_SPEED_RPM);
    
    // Move away from switch clockwise (FORWARD)
    for (int i = 0; i < 50; i++) {  // ~45° away
      motor2->onestep(FORWARD, DOUBLE);
      delay(10);
      
      if (digitalRead(LIMIT_SWITCH_PIN) == HIGH) {
        Serial.println("Switch released, continuing...");
        delay(500);
        break;
      }
    }
  }
  
  // --- STEP 2: Search for zero position ---
  Serial.println("Searching for zero position (counter-clockwise rotation)...");
  
  motor2->setSpeed(HOMING_SPEED_RPM);
  unsigned long startTime = millis();
  bool limitSwitchFound = false;
  int stepCount = 0;
  
  // Rotate counter-clockwise (BACKWARD) until detection
  while (!limitSwitchFound && (millis() - startTime < HOMING_TIMEOUT)) {
    
    // Check emergency stop
    if (emergencyStop) {
      Serial.println(">>> Homing interrupted by emergency stop <<<");
      motor2->release();
      return;
    }
    
    // Take one step
    motor2->onestep(BACKWARD, DOUBLE);
    stepCount++;
    delay(10);  // Slower delay for more precision
    
    // Check if limit switch is triggered (LOW with INPUT_PULLUP)
    if (digitalRead(LIMIT_SWITCH_PIN) == LOW) {
      limitSwitchFound = true;
      Serial.println(">>> Limit switch detected! <<<");
      Serial.print("Steps taken: ");
      Serial.println(stepCount);
      break;
    }
    
    // Display progress every 100 steps
    if (stepCount % 100 == 0) {
      Serial.print("Searching... (");
      Serial.print(stepCount);
      Serial.println(" steps)");
    }
  }
  
  // --- STEP 3: Result verification ---
  if (!limitSwitchFound) {
    Serial.println(">>> ERROR: Homing timeout <<<");
    Serial.println("Limit switch not found after 20 seconds");
    Serial.println("Checks to perform:");
    Serial.println("  - Is the switch properly wired to pin 10 and GND?");
    Serial.println("  - Is the switch mechanically accessible?");
    motor2->release();
    isHomed = false;
    return;
  }
  
  // --- STEP 4: Apply offset ---
  if (abs(TILT_HOMING_OFFSET) > 0.1) {
    Serial.print("Applying offset: ");
    Serial.print(TILT_HOMING_OFFSET);
    Serial.println("°");
    
    int offsetSteps = abs(round(TILT_HOMING_OFFSET / stepAngle2));
    uint8_t offsetDir = (TILT_HOMING_OFFSET >= 0) ? FORWARD : BACKWARD;
    
    for (int i = 0; i < offsetSteps; i++) {
      motor2->onestep(offsetDir, DOUBLE);
      delay(10);
    }
  }
  
  // --- STEP 5: Finalization ---
  delay(200);
  motor2->release();
  isHomed = true;
  
  Serial.println("=== HOMING COMPLETED SUCCESSFULLY ===");
  Serial.println("TILT zero position defined");
  Serial.println("HOMING_COMPLETE");  // Message for Python
  Serial.println();
}


// ==================== MOVEMENT COMMAND PROCESSING ====================
void processCommand(String command) {
  // Parse command in format "<angle_pan> <angle_tilt>"
  int spaceIndex = command.indexOf(' ');
  if (spaceIndex == -1) {
    Serial.println(">>> Invalid format <<<");
    Serial.println("Use: '<angle_pan> <angle_tilt>'");
    Serial.println("Example: '10 -5' for PAN +10° and TILT -5°");
    return;
  }
  
  // Extract both angles
  String angle1Str = command.substring(0, spaceIndex);
  String angle2Str = command.substring(spaceIndex + 1);
  
  float angle1 = angle1Str.toFloat();  // PAN
  float angle2 = angle2Str.toFloat();  // TILT
  
  // Optimization: If angles are negligible, no need to move
  if (abs(angle1) < 0.1 && abs(angle2) < 0.1) {
    Serial.println("Negligible angles, no movement");
    Serial.println("GOAL_REACHED");
    return;
  }
  
  // --- CALCULATE STEPS ---
  // Motor 1 (PAN): with 5:1 reduction ratio
  int steps1 = abs(round((angle1 * reductionRatio1 * 400) / 360.0));
  // Motor 2 (TILT): without reduction
  int steps2 = abs(round(angle2 / stepAngle2));
  
  // Determine directions
  uint8_t dir1 = (angle1 >= 0) ? FORWARD : BACKWARD;
  uint8_t dir2 = (angle2 >= 0) ? FORWARD : BACKWARD;
  
  // Display information
  Serial.println("--- Movement command ---");
  Serial.print("PAN:  ");
  Serial.print(angle1);
  Serial.print("° (");
  Serial.print(steps1);
  Serial.println(" steps)");
  Serial.print("TILT: ");
  Serial.print(angle2);
  Serial.print("° (");
  Serial.print(steps2);
  Serial.println(" steps)");
  
  isMoving = true;
  Serial.println("MOVING");
  
  // Restore normal speed
  motor1->setSpeed(30);
  motor2->setSpeed(30);
  
  // --- FAST MODE for small movements (<= 10 steps) ---
  if (steps1 <= 10 && steps2 <= 10) {
    for (int i = 0; i < max(steps1, steps2); i++) {
      if (emergencyStop) {
        Serial.println(">>> Movement interrupted <<<");
        isMoving = false;
        return;
      }
      
      if (i < steps1) motor1->onestep(dir1, DOUBLE);
      if (i < steps2) motor2->onestep(dir2, DOUBLE);
      
      delayMicroseconds(500);
    }
    
    isMoving = false;
    Serial.println("GOAL_REACHED");
    return;
  }
  
  // --- NORMAL MODE for larger movements ---
  unsigned long lastStatusTime = millis();
  const unsigned long STATUS_INTERVAL = 500;  // Status every 500ms
  
  int remainingSteps1 = steps1;
  int remainingSteps2 = steps2;
  
  // Movement loop with simultaneous execution of both motors
  while (remainingSteps1 > 0 || remainingSteps2 > 0) {
    // Check emergency stop
    if (emergencyStop) {
      Serial.println(">>> Movement interrupted <<<");
      isMoving = false;
      return;
    }
    
    // Send periodic status (for Python)
    unsigned long currentTime = millis();
    if (currentTime - lastStatusTime > STATUS_INTERVAL) {
      lastStatusTime = currentTime;
      Serial.print("MOVING: PAN=");
      Serial.print(remainingSteps1);
      Serial.print(" TILT=");
      Serial.println(remainingSteps2);
    }
    
    // Take one step for each motor (in parallel)
    if (remainingSteps1 > 0) {
      motor1->onestep(dir1, DOUBLE);
      remainingSteps1--;
    }
    
    if (remainingSteps2 > 0) {
      motor2->onestep(dir2, DOUBLE);
      remainingSteps2--;
    }
    
    delayMicroseconds(500);
  }
  
  // --- MOVEMENT COMPLETION CONFIRMATION ---
  isMoving = false;
  
  // Send twice to ensure reception by Python
  Serial.println("GOAL_REACHED");
  delay(50);
  Serial.println("GOAL_REACHED");
  delay(50);
  
  Serial.println("Movement completed");
  Serial.println();
}