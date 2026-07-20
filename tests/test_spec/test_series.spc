Series {
    period=12
    start=2016.1
    title="observed"
}
Transform {
    function=log
}
Arima {
    model=(0,1,1)(0,1,1)
}
x11{
	mode=mult
	seasonalma=x11default
	save=(d11 d12 d13)
}
