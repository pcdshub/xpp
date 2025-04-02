def tt_find():#tt signal find tool
            if lxt() != 0:
                print("Set current position to 0 to search") 
                return
            elif lxt() ==0:
                delayinput = 20e-9
                i = 0#iteration time
                while(1):#20ns search until finding the negarive correlation
                    print("Can you see 'Negative correlation?' y/n or quit this script q")
                    bs = input()
                    if i < 5:#100 ns is too large. If cannot find in 5 iteration need to check the other side
                        if bs == "n":
                            delayinput = -1 * abs(delayinput)
                            lxt.mvr(delayinput)
                            i = i + 1
                            print(f"Number of iteration:{i}")
                        elif bs == "y":#quit from the intial search
                            print("Switch to binary search")
                            delayinput = delayinput/2
                            break
                        elif bs == "q":
                            print("Quit")
                            return
                        else:
                            print("Please input y, n or q")
                    else:#Initial search
                        print("Search the negative correlation the other side")
                        if bs == "n":
                            delayinput = abs(delayinput)
                            lxt.mvr(delayinput)
                            i = i + 1
                            print(f"Number of iteration:{i}")
                        elif bs == "y":#quit from the intial search
                            print("Switch to binary search")
                            delayinput = delayinput/2
                            break
                        elif bs == "q":
                            print("Quit")
                            return
                        else:
                            print("Please input y, n or q")
                 


                while(abs(delayinput) > 0.5e-12):#binary search from 20ns to 0.5ps
                    print("Can you see 'Negative correlation now'? y/n or quit this script q")
                    bs = input()
                    if bs == "n":
                        delayinput = -1 * abs(delayinput)
                        lxt.mvr(delayinput)
                        delayinput = delayinput/2
                        i = i + 1
                        print(f"Number of iteration:{i}")
                    elif bs == "y":
                        delayinput = abs(delayinput)
                        lxt.mvr(delayinput)
                        delayinput = delayinput/2
                        i = i + 1
                        print(f"Number of iteration:{i}")
                    elif bs == "q":
                        print("Quit")
                        return
                    else:
                        print("Please input y, n or q")
                ttdata = np.zeros([120,])#timetool signal search at the initial position
                for ii in range(120):
                    current_tt, ttamp, ipm2val, ttfwhm = las.get_ttall()
                    if (ttamp > 0.03)and(ttfwhm < 130)and(ttfwhm >  70):
                        ttdata[ii,0] = ttamp
                if np.count_nonzero(ttdata) > 30:#If we have timetool signal more than 1/4 of 120 shots, this script is stopped
                    print("Found timetool signal ")
                    return
                else: #scan from -1.0 to 1.0 ps to find timetool signal around here until finding timetool signal
                    lxt.mvr(-1e-12)
                            
                    while(1):
                        ttdata = np.zeros([120,])
                        ii = 0
                        for ii in range(120):
                            current_tt, ttamp, ipm2val, ttfwhm = las.get_ttall()#scan from -1.5 to 1.5 ps to find timetool signal
                            if (ttamp > 0.03)and(ttfwhm < 130)and(ttfwhm >  70):
                                ttdata[ii,0] = ttamp
                        if np.count_nonzero(ttdata) > 30:
                            break
                        else:
                            lxt.mvr(0.5e-12)
                            print(f"searching timetool signal {lxt()}")
                          
                    
                print("Found timetool signal and set current lxt to 0")
                lxt.set_current_position(0)
            return
