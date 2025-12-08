#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for fluorescence sensor integration
Simple validation that the sensor is working correctly
"""

import sys
import time
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.hardware.fluo_controller import FluoController

def test_fluorescence_sensor():
    """Test the fluorescence sensor independently"""
    print("=== Fluorescence Sensor Test ===")
    print("This test validates the simplified fluorescence sensor integration")
    print()
    
    try:
        # Step 1: Initialize sensor (ROMI pattern)
        print("Step 1/4: Initializing fluorescence sensor...")
        fluo = FluoController("fluo", "fluo")  # No separate connect() needed
        print("✅ Sensor initialized successfully")
        print()
        
        # Step 2: Check device status
        print("Step 2/4: Checking device status...")
        status = fluo.get_device_status()
        print(f"   Connected: {status['connected']}")
        print(f"   Status: {status['status']}")
        
        if not status['connected']:
            print("⚠️  Device not connected - cannot perform measurement test")
            return False
        
        print("✅ Device is connected and ready")
        print()
        
        # Step 3: Perform test measurement
        print("Step 3/4: Performing test measurement...")
        print("   Using default sensor configuration...")
        
        start_time = time.time()
        measurements = fluo.measure_simple()
        measurement_time = time.time() - start_time
        
        if measurements:
            print(f"✅ Measurement successful!")
            print(f"   Duration: {measurement_time:.2f} seconds")
            print(f"   Data points: {len(measurements)}")
            print(f"   First value: {measurements[0]:.6f}")
            print(f"   Last value: {measurements[-1]:.6f}")
            print(f"   Average: {sum(measurements)/len(measurements):.6f}")
            print(f"   Min: {min(measurements):.6f}")
            print(f"   Max: {max(measurements):.6f}")
        else:
            print("❌ No measurements received")
            return False
        
        print()
        
        # Step 4: Multiple measurements test
        print("Step 4/4: Testing multiple measurements...")
        
        num_tests = 3
        all_successful = True
        
        for i in range(num_tests):
            print(f"   Test {i+1}/{num_tests}...")
            test_measurements = fluo.measure_simple()
            
            if test_measurements:
                avg = sum(test_measurements) / len(test_measurements)
                print(f"   ✅ Test {i+1}: {len(test_measurements)} points, avg = {avg:.6f}")
            else:
                print(f"   ❌ Test {i+1}: Failed")
                all_successful = False
            
            # Small delay between measurements
            if i < num_tests - 1:
                time.sleep(1)
        
        if all_successful:
            print(f"\n✅ All {num_tests} tests successful!")
            print("\n🧬 Fluorescence sensor is ready for integration with targeting system")
            return True
        else:
            print(f"\n⚠️  Some tests failed - check sensor configuration")
            return False
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return False
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("Fluorescence Sensor Integration Test")
    print("=" * 40)
    print()
    
    success = test_fluorescence_sensor()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 TEST PASSED - Sensor ready for targeting integration")
        print("\nNext step: Run targeting with fluorescence:")
        print("   python scripts/run_targeting_fluo.py pointcloud.ply --simulate")
    else:
        print("❌ TEST FAILED - Check sensor configuration")
        print("\nTroubleshooting:")
        print("   1. Verify sensor is connected and powered")
        print("   2. Check RCom configuration") 
        print("   3. Test original romi_fluo.py script")
        print("   4. Use --no-fluorescence option to test without sensor")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
