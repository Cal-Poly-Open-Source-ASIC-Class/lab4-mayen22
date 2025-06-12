module afifo #(
    parameter DATA_WIDTH = 8,
    parameter ADDR_WIDTH = 3
) (
    // Write stuff
    input i_wclk, i_wrst_n, i_wr_en,
    input [DATA_WIDTH-1:0] i_wdata,
    output o_wfull,

    // Read stuff
    input i_rclk, i_rrst_n, i_rd_en,
    output [DATA_WIDTH-1:0] o_rdata,
    output o_rempty
);
    // Pointers
    logic [ADDR_WIDTH:0] wbin;
    logic [ADDR_WIDTH:0] rbin;

    logic [DATA_WIDTH-1:0] mem [0:(1<<ADDR_WIDTH)-1];

    logic [ADDR_WIDTH:0] wgray, rgray;
    logic [ADDR_WIDTH:0] rq1_wgray, rq2_wgray;
    logic [ADDR_WIDTH:0] wq1_rgray, wq2_rgray;

    // Write
    always @(posedge i_wclk) begin
        // Reset must be synchronous otherwise lint warnings
        if (!i_wrst_n) begin
            wbin <= 0;
            wq1_rgray <= 0;
            wq2_rgray <= 0;
        end
        if ((i_wr_en)&&(!o_wfull)) begin
            wbin <= wbin + 1;
            mem[wbin[ADDR_WIDTH-1:0]] <= i_wdata;
        end
        // Gray coding
        wgray <= (wbin >> 1) ^ wbin;
        // Synchronize
        wq1_rgray <= rgray;
        wq2_rgray <= wq1_rgray;
    end

    // Read
    always @(posedge i_rclk) begin
        if (!i_rrst_n) begin
            rbin <= 0;
            rq1_wgray <= 0;
            rq2_wgray <= 0;
        end
        if ((i_rd_en)&&(!o_rempty)) begin
            rbin <= rbin + 1;
        end
        // Gray coding
        rgray <= (rbin >> 1) ^ rbin;
        // Synchronize
        rq1_wgray <= wgray;
        rq2_wgray <= rq1_wgray;
    end

    // Outputs
    assign o_rdata = mem[rbin[ADDR_WIDTH-1:0]];

    // Check for wrapping/lapped behavior
    assign o_wfull = (wgray[ADDR_WIDTH:ADDR_WIDTH-1] == ~wq2_rgray[ADDR_WIDTH:ADDR_WIDTH-1]) &&
                     (wgray[ADDR_WIDTH-2:0] == wq2_rgray[ADDR_WIDTH-2:0]);

    assign o_rempty = (rgray == rq2_wgray);

endmodule